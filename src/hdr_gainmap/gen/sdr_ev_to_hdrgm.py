from pathlib import Path

from hdr_gainmap.preset import Preset
from hdr_gainmap.gen.base_gen import BaseGen
from hdr_gainmap.image import image_tools


class SdrToHdrgm(BaseGen):
    _ev: float

    def __init__(
        self,
        sdr_path: Path,
        ev: float = 2.0,
        hdrgm_path: Path | None = None,
        preset: Preset = Preset.default,
        tag: bool = False,
        keep_temp_files: bool = False,
    ) -> None:
        super().__init__(sdr_path, hdrgm_path, preset, tag, keep_temp_files)
        self._ev = ev

    def _load_images(self) -> None:
        """Load SDR image."""
        (
            self._sdr_np_image,
            self._sdr_rgb_profile,
            self._sdr_exif_bytes,
            self._sdr_icc_bytes,
        ) = image_tools.open_sdr_image(self._sdr_path)

    def _process_images(self) -> None:
        """Get linear SDR image and apply EV to create HDR."""
        self._sdr_np_image_linear = image_tools.get_linear_image(
            image=self._sdr_np_image,
            rgb_profile=self._sdr_rgb_profile,
        )

        self._hdr_np_image_linear = self._sdr_np_image_linear * pow(2, self._ev)

    def validate(self) -> None:
        super().validate()
        if not (-5 <= self._ev <= 5):
            raise ValueError("EV value must be in [-5,5]")
