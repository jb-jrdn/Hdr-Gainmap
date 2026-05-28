from pathlib import Path

import numpy as np
import colour
import cv2
from hdrconv.core import GainmapMetadata, GainmapImage
from hdrconv.io import write_21496
from hdr_gainmap.preset import Preset
from hdr_gainmap.hdrgm.hdrgm_settings import HdrgmSettings, HDRGM_SETTINGS

DEFAULT_OFFSET = 1 / 64
DEFAULT_GAMMA = 1.0


def get_optimized_gain(
    gain: np.ndarray,
    percentile: float = 99.998,
) -> np.ndarray:
    """
    Compress extreme gain values to reduce outliers.

    Args:
        gain: Per-pixel gain (H, W, 3).
        percentile: Upper percentile used to limit highlights.

    Returns:
        Gain array with reduced extreme values.
    """
    max_rgb = np.max(gain, axis=-1)

    p_low = np.percentile(max_rgb, percentile - 0.01)
    p_high = np.percentile(max_rgb, percentile)
    gmax = max_rgb.max()

    print(f"optim param -> max: {gmax:.2f} | p_low: {p_low:.2f} | p_high: {p_high:.2f}")

    eps = 1e-8
    scale = (p_high - p_low) / (gmax - p_low + eps)

    mapped = max_rgb.copy()
    mask = mapped > p_low
    mapped[mask] = p_low + (mapped[mask] - p_low) * scale

    ratio = mapped / (max_rgb + eps)

    optimized_gain = gain * ratio[..., None]
    return optimized_gain


def get_gainmap(
    sdr_np_image_linear: np.ndarray,
    hdr_np_image_linear: np.ndarray,
    hdrgm_settings: HdrgmSettings,
) -> tuple[np.ndarray, float, float]:
    """
    Compute gain map from SDR and HDR linear images.

    Args:
        sdr_np_image_linear: SDR image in linear space.
        hdr_np_image_linear: HDR image in linear space.
        hdrgm_settings: Settings controlling gain map generation.

    Returns:
        gainmap: 8-bit normalized gain map.
        min_gain_ev: Minimum EV per channel.
        max_gain_ev: Maximum EV per channel.
    """
    gain = (hdr_np_image_linear + DEFAULT_OFFSET) / (sdr_np_image_linear + DEFAULT_OFFSET)
    gain = get_optimized_gain(gain)
    gain_ev = np.log2(gain)

    # resize gain map if needed
    if hdrgm_settings.gain_map_size_factor > 1:
        height, width = gain_ev.shape[:2]
        new_width = int(width // hdrgm_settings.gain_map_size_factor)
        new_height = int(height // hdrgm_settings.gain_map_size_factor)
        gain_ev = cv2.resize(gain_ev, (new_width, new_height))

    if hdrgm_settings.is_multichannel:
        min_gain_ev_np = np.min(gain_ev, axis=(0, 1))
        max_gain_ev_np = np.max(gain_ev, axis=(0, 1))
    else:
        min_val = np.min(gain_ev)
        max_val = np.max(gain_ev)
        min_gain_ev_np = np.array([min_val, min_val, min_val])
        max_gain_ev_np = np.array([max_val, max_val, max_val])

    min_gain_ev_np = np.maximum(min_gain_ev_np, hdrgm_settings.min_gain_ev)
    max_gain_ev_np = np.minimum(max_gain_ev_np, hdrgm_settings.max_gain_ev)

    min_gain_ev = min_gain_ev_np.reshape((1, 1, -1))
    max_gain_ev = max_gain_ev_np.reshape((1, 1, -1))

    gain_ev_norm = (gain_ev - min_gain_ev) / (max_gain_ev - min_gain_ev)
    gain_ev_norm = np.clip(gain_ev_norm, 0.0, 1.0)
    gain_ev_norm = np.power(gain_ev_norm, DEFAULT_GAMMA)
    gainmap = np.round(gain_ev_norm * 255).astype(np.uint8)

    min_gain_ev = tuple(min_gain_ev_np.tolist())
    max_gain_ev = tuple(max_gain_ev_np.tolist())

    print(f"min_ev: {min_gain_ev[0]:.2f}, {min_gain_ev[1]:.2f}, {min_gain_ev[2]:.2f}")
    print(f"max_ev: {max_gain_ev[0]:.2f}, {max_gain_ev[1]:.2f}, {max_gain_ev[2]:.2f}")

    return gainmap, min_gain_ev, max_gain_ev


def get_metadata(
    min_gain_ev: tuple,
    max_gain_ev: tuple,
    hdrgm_settings: HdrgmSettings,
) -> GainmapMetadata:
    """
    Create metadata describing gain map encoding.

    Args:
        min_gain_ev: Minimum EV values per channel.
        max_gain_ev: Maximum EV values per channel.
        hdrgm_settings: Settings for HDR gain map.

    Returns:
        GainmapMetadata object.
    """
    used_alternate_hdr_headroom = max(max_gain_ev)
    if hdrgm_settings.forced_max_hdr_capacity:
        used_alternate_hdr_headroom = hdrgm_settings.forced_max_hdr_capacity
    return GainmapMetadata(
        minimum_version=0,
        writer_version=0,
        baseline_hdr_headroom=0.0,
        alternate_hdr_headroom=used_alternate_hdr_headroom,
        is_multichannel=hdrgm_settings.is_multichannel,
        use_base_colour_space=True,
        gainmap_min=min_gain_ev,
        gainmap_max=max_gain_ev,
        gainmap_gamma=(DEFAULT_GAMMA, DEFAULT_GAMMA, DEFAULT_GAMMA),
        baseline_offset=(DEFAULT_OFFSET, DEFAULT_OFFSET, DEFAULT_OFFSET),
        alternate_offset=(DEFAULT_OFFSET, DEFAULT_OFFSET, DEFAULT_OFFSET),
    )


def create_hdrgm(
    sdr_np_image_linear: np.ndarray,
    hdr_np_image_linear: np.ndarray,
    sdr_rgb_profile: colour.RGB_Colourspace,
    sdr_icc_bytes: bytes,
    output_path: Path,
    preset: Preset = Preset.default,
    keep_temp_files: bool = False,
) -> None:
    """
    Generate and write an HDR gain map file.

    Args:
        sdr_np_image_linear: SDR image in linear space.
        hdr_np_image_linear: HDR image in linear space.
        sdr_rgb_profile: SDR color space for encoding.
        sdr_icc_bytes: ICC profile for SDR image.
        output_path: Output file path.
        preset: Preset name for settings.
        keep_temp_files: Save intermediate gain map image if True.
    """
    hdrgm_settings = HDRGM_SETTINGS[preset]
    sdr_np_image = sdr_rgb_profile.cctf_encoding(sdr_np_image_linear)

    gainmap, min_gain_ev, max_gain_ev = get_gainmap(
        sdr_np_image_linear=sdr_np_image_linear,
        hdr_np_image_linear=hdr_np_image_linear,
        hdrgm_settings=hdrgm_settings,
    )

    metadata = get_metadata(
        min_gain_ev=min_gain_ev,
        max_gain_ev=max_gain_ev,
        hdrgm_settings=hdrgm_settings,
    )

    gainmapImage = GainmapImage(
        baseline=sdr_np_image,
        gainmap=gainmap,
        metadata=metadata,
        baseline_icc=sdr_icc_bytes,
        gainmap_icc=None,
    )

    write_21496(
        data=gainmapImage,
        filepath=output_path,
        baseline_quality=hdrgm_settings.sdr_quality,
        gainmap_quality=hdrgm_settings.gain_map_quality,
    )

    if keep_temp_files:
        cv2.imwrite(
            output_path.with_stem(output_path.stem + "_gm"),
            cv2.cvtColor(gainmap, cv2.COLOR_RGB2BGR),
            [cv2.IMWRITE_JPEG_QUALITY, hdrgm_settings.gain_map_quality],
        )
