import os
from tools.uhdr import UltraHdr
from tools import image_tools

class SdrSdrEvToUhdr:

    def __init__(
        self,
        sdr_path: str,
        sdr_ev_path: str,
        ev: float = 2.0,
        uhdr_path: str | None = None,
        tag: bool = False,
        keep_temp_files: bool = False,
    ) -> None:
        self.sdr_path = sdr_path
        self.sdr_ev_path = sdr_ev_path
        self.ev = ev
        self.uhdr_path = uhdr_path
        self.tag = tag
        self.keep_temp_files = keep_temp_files

    def run(self) -> None:
        # load images
        sdr_np_image, sdr_rgb_profile = image_tools.open_sdr_image(self.sdr_path)
        sdr_ev_np_image, sdr_ev_rgb_profile = image_tools.open_sdr_image(self.sdr_ev_path)

        # get rgb linear values
        sdr_np_image_linear = image_tools.get_linear_image(
            image=sdr_np_image,
            rgb_profile=sdr_rgb_profile,
        )
        sdr_ev_np_image_linear = image_tools.get_linear_image(
            image=sdr_ev_np_image,
            rgb_profile=sdr_ev_rgb_profile,
        )

        # get hdr image
        hdr_np_image_linear = image_tools.get_hdr_from_sdr_stacking(
            sdr_np_linear=sdr_np_image_linear,
            sdr_rgb_profile=sdr_rgb_profile,
            sdr_ev_np_linear=sdr_ev_np_image_linear,
            sdr_ev_rgb_profile=self.sdr_ev_rgb_profile,
            ev=self.ev,
        )

        # Add Hdr tag if asked
        if self.tag:
            image_tools.add_hdr_tag(
                sdr_np_image_linear=sdr_np_image_linear,
                hdr_np_image_linear=hdr_np_image_linear,
            )

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
        if not os.path.isfile(self.sdr_ev_path):
            raise FileNotFoundError(f"Sdr ev image not found: {self.sdr_ev_path}")
        if not (-5.01 < self.ev < 5.01):
            raise ValueError(f"EV value must be in [-5,5]")
