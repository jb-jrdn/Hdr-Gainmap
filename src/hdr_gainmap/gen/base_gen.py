from pathlib import Path
from abc import ABC, abstractmethod

import colour
import numpy as np

from hdr_gainmap.preset import Preset
from hdr_gainmap.image import image_tools
from hdr_gainmap.image.image_settings import IMAGE_SETTINGS, ImageSettings
from hdr_gainmap.hdrgm.hdrgm import create_hdrgm


class BaseGen(ABC):
    """Abstract base class for hdr gainmap gen"""

    _sdr_path: Path
    _hdrgm_path: Path
    _preset: Preset
    _settings: ImageSettings
    _tag: bool
    _keep_temp_files: bool
    _sdr_changed: bool
    _sdr_np_image: np.ndarray
    _sdr_np_image_linear: np.ndarray
    _hdr_np_image_linear: np.ndarray
    _sdr_rgb_profile: colour.RGB_Colourspace
    _sdr_exif_bytes: bytes
    _sdr_icc_bytes: bytes

    def __init__(
        self,
        sdr_path: Path,
        hdrgm_path: Path | None = None,
        preset: Preset = Preset.default,
        tag: bool = False,
        keep_temp_files: bool = False,
    ) -> None:
        self._sdr_path = sdr_path
        self._hdrgm_path = (
            self._sdr_path.with_stem(self._sdr_path.stem + "_hdrgm") if hdrgm_path is None else hdrgm_path
        )
        self._preset = Preset(preset)
        self._settings = IMAGE_SETTINGS[preset]
        self._tag = tag
        self._keep_temp_files = keep_temp_files
        self._sdr_changed = False

    def run(self) -> None:
        """Main execution pipeline."""
        # Load input images
        self._load_images()

        # Preprocessing
        self._apply_crop_and_resize()

        # Get linear images and process
        self._process_images()

        # Add HDR tag if requested
        self._apply_hdr_tag()

        # Generate gainmap
        self._create_gainmap()

        # Save temporary files if requested
        self._save_temp_files()

    @abstractmethod
    def _load_images(self) -> None:
        """Load input images. Each subclass implements its own loading logic."""

    @abstractmethod
    def _process_images(self) -> None:
        """Process images to generate linear HDR. Each subclass implements specific logic."""

    def _apply_crop_and_resize(self) -> None:
        """Apply cropping and resizing based on settings."""
        if self._settings.min_ratio_w_h or self._settings.max_ratio_w_h:
            self._sdr_np_image = image_tools.crop_to_ratio(
                img=self._sdr_np_image,
                min_ratio=self._settings.min_ratio_w_h,
                max_ratio=self._settings.max_ratio_w_h,
            )
            self._sdr_changed = True

        if self._settings.width_max or self._settings.height_max:
            self._sdr_np_image = image_tools.resize_to_max(
                img=self._sdr_np_image,
                width_max=self._settings.width_max,
                height_max=self._settings.height_max,
            )
            self._sdr_changed = True

    def _apply_hdr_tag(self) -> None:
        """Apply HDR tag if requested."""
        if self._tag:
            image_tools.add_hdr_tag(
                sdr_np_image_linear=self._sdr_np_image_linear,
                hdr_np_image_linear=self._hdr_np_image_linear,
            )
            self._sdr_changed = True

    def _create_gainmap(self) -> None:
        """Create the HDRGM image."""
        create_hdrgm(
            sdr_np_image_linear=self._sdr_np_image_linear,
            hdr_np_image_linear=self._hdr_np_image_linear,
            sdr_rgb_profile=self._sdr_rgb_profile,
            sdr_icc_bytes=self._sdr_icc_bytes,
            output_path=self._hdrgm_path,
            preset=self._preset,
            keep_temp_files=self._keep_temp_files,
        )

    def _save_temp_files(self) -> None:
        """Save temporary SDR file if requested."""
        if self._sdr_changed and self._keep_temp_files:
            sdr_path = self._sdr_path.with_stem(self._sdr_path.stem + "_temp")
            image_tools.save_sdr_image(
                sdr_np_image_linear=self._sdr_np_image_linear,
                rgb_profile=self._sdr_rgb_profile,
                sdr_path=sdr_path,
                exif_bytes=self._sdr_exif_bytes,
                icc_bytes=self._sdr_icc_bytes,
            )

    def validate(self) -> None:
        """Validate input files. Each subclass implements its own validation."""
        if not self._sdr_path.is_file():
            raise FileNotFoundError(f"Sdr image not found: {self._sdr_path}")
