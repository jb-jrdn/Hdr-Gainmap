from pathlib import Path

import colour
import numpy as np

from hdr_gainmap.preset import Preset
from hdr_gainmap.gen.base_gen import BaseGen
from hdr_gainmap.image import image_tools


class SdrHdrToHdrgm(BaseGen):
    _hdr_path: Path
    _hdr_np_image: np.ndarray
    _hdr_rgb_profile: colour.RGB_Colourspace

    def __init__(
        self,
        sdr_path: Path,
        hdr_path: Path,
        hdrgm_path: Path | None = None,
        preset: Preset = Preset.default,
        tag: bool = False,
        keep_temp_files: bool = False,
    ) -> None:
        super().__init__(sdr_path, hdrgm_path, preset, tag, keep_temp_files)
        self._hdr_path = hdr_path

    def _load_images(self) -> None:
        """Load SDR and HDR images."""
        (
            self._sdr_np_image,
            self._sdr_rgb_profile,
            self._sdr_exif_bytes,
            self._sdr_icc_bytes,
        ) = image_tools.open_sdr_image(self._sdr_path)
        self._hdr_np_image, self._hdr_rgb_profile = image_tools.open_hdr_avif_image(self._hdr_path)

        # check sizes consistency
        if self._sdr_np_image.shape[:2] != self._hdr_np_image.shape[:2]:
            raise ValueError("Sdr and Hdr image sizes are not identical")

    def _apply_crop_and_resize(self) -> None:
        """Apply cropping and resizing to both SDR and HDR images."""
        super()._apply_crop_and_resize()
        if self._settings.min_ratio_w_h or self._settings.max_ratio_w_h:
            self._hdr_np_image = image_tools.crop_to_ratio(
                img=self._hdr_np_image,
                min_ratio=self._settings.min_ratio_w_h,
                max_ratio=self._settings.max_ratio_w_h,
            )

        if self._settings.width_max or self._settings.height_max:
            self._hdr_np_image = image_tools.resize_to_max(
                img=self._hdr_np_image,
                width_max=self._settings.width_max,
                height_max=self._settings.height_max,
            )

    def _process_images(self) -> None:
        """Get linear images and convert HDR to SDR primaries."""
        self._sdr_np_image_linear = image_tools.get_linear_image(
            image=self._sdr_np_image,
            rgb_profile=self._sdr_rgb_profile,
        )
        self._hdr_np_image_linear = image_tools.get_linear_image(
            image=self._hdr_np_image,
            rgb_profile=self._hdr_rgb_profile,
            is_hdr=True,
        )

        # convert hdr values to the sdr primaries
        self._hdr_np_image_linear = image_tools.get_adapted_rgb_primaries(
            image=self._hdr_np_image_linear,
            origin_rgb_profile=self._hdr_rgb_profile,
            new_rgb_profile=self._sdr_rgb_profile,
            is_hdr=True,
        )

    def validate(self) -> None:
        super().validate()
        if not self._hdr_path.is_file():
            raise FileNotFoundError(f"Hdr image file not found: {self._hdr_path}")


def process_folder(
    input_directory: Path,
    preset: Preset = Preset.default,
    tag: bool = False,
    overwrite_existing: bool = False,
    keep_temp_files: bool = False,
) -> None:
    """
    Processes all JPG images in the specified directory to generate UHDR images.
    For each JPG file, if a corresponding AVIF file exists, generates a UHDR image.
    Skips processing if the UHDR output already exists and `overwrite_existing` is False.

    Args:
        input_directory: Path to the directory containing JPG and AVIF files.
        preset: Preset for process.
        tag: Add hdr tag on image. Defaults to False.
        overwrite_existing: If True, overwrites existing UHDR files. Defaults to False.
        keep_temp_files: If True, retains temporary files after processing. Defaults to False.

    Raises:
        FileNotFoundError: If "input_directory" does not exist or is not a directory.
        ValueError: If no valid JPG/AVIF pairs are found in the directory.
    """
    if not input_directory.is_dir():
        raise FileNotFoundError(f"Directory does not exist: {input_directory}")

    for filename in input_directory.iterdir():
        hdrgm_output_filepath = filename.with_stem(filename.stem + "_uhdr")
        if not overwrite_existing and hdrgm_output_filepath.is_file():
            continue

        if filename.suffix.lower() == ".jpg":
            corresponding_avif_filepath = filename.with_suffix(".avif")

            if corresponding_avif_filepath.is_file():
                print(f"Processing file: {filename}")
                process = SdrHdrToHdrgm(
                    sdr_path=filename,
                    hdr_path=corresponding_avif_filepath,
                    preset=preset,
                    tag=tag,
                    keep_temp_files=keep_temp_files,
                )
                process.validate()
                process.run()
