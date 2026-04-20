from dataclasses import dataclass
from preset import Preset


@dataclass
class UhdrSettings:
    min_gain: float = 0.5
    max_gain: float = 10000/203
    gain_map_quality: int = 90
    gain_map_size_factor: int = 1
    forced_max_hdr_capacity: float | None = None


PRESETS = {
    Preset.default: UhdrSettings(),
    Preset.best: UhdrSettings(
        min_gain = 0.2,
        gain_map_quality = 100,
    ),
    Preset.light: UhdrSettings(
        gain_map_quality = 80,
        gain_map_size_factor = 2,
    ),
    Preset.insta: UhdrSettings(
        min_gain = 1.0,
        max_gain = 32.0,
    ),
}
