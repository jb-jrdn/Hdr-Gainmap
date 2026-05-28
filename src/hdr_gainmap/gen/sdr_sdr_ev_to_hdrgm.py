from pathlib import Path

import colour
import numpy as np

from hdr_gainmap.preset import Preset
from hdr_gainmap.gen.base_gen import BaseGen
from hdr_gainmap.image import image_tools


class SdrSdrEvToHdrgm(BaseGen):
    _sdr_ev_path: Path
    _ev: float
    _sdr_ev_np_image: np.ndarray
    _sdr_ev_rgb_profile: colour.RGB_Colourspace

    def __init__(
        self,
        sdr_path: Path,
        sdr_ev_path: Path,
        ev: float = 2.0,
        hdrgm_path: Path | None = None,
        preset: Preset = Preset.default,
        tag: bool = False,
        keep_temp_files: bool = False,
    ) -> None:
        super().__init__(sdr_path, hdrgm_path, preset, tag, keep_temp_files)
        self._sdr_ev_path = sdr_ev_path
        self._ev = ev

    def _load_images(self) -> None:
        """Load SDR and SDR EV images."""
        (
            self._sdr_np_image,
            self._sdr_rgb_profile,
            self._sdr_exif_bytes,
            self._sdr_icc_bytes,
        ) = image_tools.open_sdr_image(self._sdr_path)
        self._sdr_ev_np_image, self._sdr_ev_rgb_profile, _, _ = image_tools.open_sdr_image(self._sdr_ev_path)

        # check sizes consistency
        if self._sdr_np_image.shape[:2] != self._sdr_ev_np_image.shape[:2]:
            raise ValueError("Sdr and SdrEv image sizes are not identical")

    def _apply_crop_and_resize(self) -> None:
        """Apply cropping and resizing to both SDR images."""
        super()._apply_crop_and_resize()
        if self._settings.min_ratio_w_h or self._settings.max_ratio_w_h:
            self._sdr_ev_np_image = image_tools.crop_to_ratio(
                img=self._sdr_ev_np_image,
                min_ratio=self._settings.min_ratio_w_h,
                max_ratio=self._settings.max_ratio_w_h,
            )
            self._sdr_changed = True

        if self._settings.width_max or self._settings.height_max:
            self._sdr_ev_np_image = image_tools.resize_to_max(
                img=self._sdr_ev_np_image,
                width_max=self._settings.width_max,
                height_max=self._settings.height_max,
            )

    def _process_images(self) -> None:
        """Get linear images and create HDR from SDR stacking."""
        self._sdr_np_image_linear = image_tools.get_linear_image(
            image=self._sdr_np_image,
            rgb_profile=self._sdr_rgb_profile,
        )
        sdr_ev_np_image_linear = image_tools.get_linear_image(
            image=self._sdr_ev_np_image,
            rgb_profile=self._sdr_ev_rgb_profile,
        )

        # get hdr image
        self._hdr_np_image_linear = image_tools.get_hdr_from_sdr_stacking(
            sdr_np_linear=self._sdr_np_image_linear,
            sdr_rgb_profile=self._sdr_rgb_profile,
            sdr_ev_np_linear=sdr_ev_np_image_linear,
            sdr_ev_rgb_profile=self._sdr_ev_rgb_profile,
            ev=self._ev,
        )

    def validate(self) -> None:
        super().validate()
        if not self._sdr_ev_path.is_file():
            raise FileNotFoundError(f"Sdr ev image not found: {self._sdr_ev_path}")
        if not (-5 <= self._ev <= 5):
            raise ValueError("EV value must be in [-5,5]")
