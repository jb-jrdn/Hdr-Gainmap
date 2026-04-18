from dataclasses import dataclass


@dataclass
class UhdrMetadata:
    min_content_boost: float | None = None  # depends of gain map
    max_content_boost: float | None = None  # depends of gain map
    gamma: float = 1.0
    sdr_offset: float = 1/64
    hdr_offset: float = 1/64
    min_hdr_capacity: float = 1.0
    max_hdr_capacity: float = 10000/203
    use_base_color_space: int = 1

    def is_valid(self) -> bool:
        return (
            self.min_content_boost is not None and
            self.max_content_boost is not None and
            self.max_hdr_capacity >= 1 and 
            self.min_hdr_capacity >= 1 and
            self.max_content_boost >= self.min_content_boost and
            self.sdr_offset > 0 and
            self.hdr_offset > 0 and
            self.use_base_color_space in [0,1]
        )
