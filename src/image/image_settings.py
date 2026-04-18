from dataclasses import dataclass
from preset import Preset
from uhdr.uhdr_settings import UhdrSettings, PRESETS as UHDR_PRESETS


@dataclass
class ImageSettings:
    min_ratio_w_h: float | None = None
    max_ratio_w_h: float | None = None
    width_max: int | None = None
    height_max: int | None = None
    quality: int = 95
    output_rgb_profile: str | None = None
    uhdr_settings: UhdrSettings = UhdrSettings()


PRESETS = {
    Preset.default: ImageSettings(),
    Preset.best: ImageSettings(
        quality = 100,
        uhdr_settings = UHDR_PRESETS[Preset.best],
    ),
    Preset.light: ImageSettings(
        quality = 80,
        uhdr_settings = UHDR_PRESETS[Preset.light],
    ),
    Preset.insta: ImageSettings(
        min_ratio_w_h = 0.8,
        max_ratio_w_h = 1.91,
        width_max = 1080,
        height_max = 1350,
        quality = 100,
        output_rgb_profile = "Display P3",
        uhdr_settings = UHDR_PRESETS[Preset.insta],
    ),
}
