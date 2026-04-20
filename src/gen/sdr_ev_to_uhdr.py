import os
from uhdr.uhdr import UltraHdr
from image import image_tools

class SdrToUhdr:

    def __init__(
        self,
        sdr_path: str,
        ev: float = 2.0,
        uhdr_path: str | None = None,
        keep_temp_files: bool = False,
    ) -> None:
        self.sdr_path = sdr_path
        self.ev = ev
        self.uhdr_path = uhdr_path
        self.keep_temp_files = keep_temp_files

    def run(self) -> None:
        # load image
        sdr_np_image, sdr_rgb_profile, exif = image_tools.open_sdr_image(self.sdr_path)

        # get rgb linear values
        sdr_np_image_linear = image_tools.get_linear_image(
            image=sdr_np_image,
            rgb_profile=sdr_rgb_profile,
        )

        # apply ev
        hdr_np_image_linear = sdr_np_image_linear * pow(2, self.ev)

        # create uhdr image
        UltraHdr.create_uhdr_image_from_sdr_and_hdr_data(
            sdr_np_image_linear=sdr_np_image_linear,
            hdr_np_image_linear=hdr_np_image_linear,
            sdr_path=self.sdr_path,
            output_uhdr_path=self.uhdr_path,
            keep_temp_files=self.keep_temp_files,
        )

    def validate(self) -> None:
        if not os.path.isfile(self.sdr_path):
            raise FileNotFoundError(f"Sdr image not found: {self.sdr_path}")
        if not (-5.01 < self.ev < 5.01):
            raise ValueError(f"EV value must be in [-5,5]")
