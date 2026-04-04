import os
from tools import uhdr_tools, image_tools

class SdrSdrEvToUhdr:

    def __init__(
        self,
        sdr_path: str,
        sdr_ev_path: str,
        ev: float = 2.0,
        uhdr_path: str | None = None,
        keep_temp_files: bool = False,
    ) -> None:
        self.sdr_path = sdr_path
        self.sdr_np_image = None
        self.sdr_rgb_profile = None

        self.sdr_ev_path = sdr_ev_path
        self.sdr_ev_np_image = None
        self.sdr_ev_rgb_profile = None

        self.ev = ev

        self.uhdr_path = uhdr_path

        self.gainmap_path = None
        self.gainmap_np_image = None

        self.metadata_path = None
        self.metadata = uhdr_tools.UhdrMetadata()

        self.keep_temp_files = keep_temp_files

    def run(self) -> None:
        # load images
        self.sdr_np_image, self.sdr_rgb_profile = image_tools.open_sdr_image(self.sdr_path)
        self.sdr_ev_np_image, self.sdr_ev_rgb_profile = image_tools.open_sdr_image(self.sdr_ev_path)

        # linearize
        sdr_np_image_linear = image_tools.get_linear_image(
            image=self.sdr_np_image,
            rgb_profile=self.sdr_rgb_profile,
        )
        sdr_ev_np_image_linear = image_tools.get_linear_image(
            image=self.sdr_ev_np_image,
            rgb_profile=self.sdr_ev_rgb_profile,
        )

        # get hdr image
        hdr_np_image_linear = image_tools.get_hdr_from_sdr_stacking(
            sdr_np_linear=sdr_np_image_linear,
            sdr_rgb_profile=self.sdr_rgb_profile,
            sdr_ev_np_linear=sdr_ev_np_image_linear,
            sdr_ev_rgb_profile=self.sdr_ev_rgb_profile,
            ev=self.ev,
        )

        # process gain map
        self.gainmap_np_image, min_map, max_map = uhdr_tools.get_uhdr_gainmap(
            sdr_np_image_linear=sdr_np_image_linear,
            hdr_np_image_linear=hdr_np_image_linear,
            metadata=self.metadata,
        )

        # save gain map
        uhdr_tools.write_gainmap(
            gainmap=self.gainmap_np_image,
            gainmap_path=self.gainmap_path,
        )

        # create metadata file
        self.metadata.min_content_boost = min_map
        self.metadata.max_content_boost = max_map
        uhdr_tools.create_uhdr_metadata(
            metadata=self.metadata,
            metadata_path=self.metadata_path,
        )

        # create uhdr image with ultrahdr_app
        uhdr_tools.create_uhdr_image_from_sdr_and_gainmap(
            sdr_path=self.sdr_path,
            gainmap_path=self.gainmap_path,
            metadata_path=self.metadata_path,
            output_uhdr_path=self.uhdr_path,
        )

        # delete temp files if needed
        if not self.keep_temp_files:
            os.remove(self.gainmap_path)
            os.remove(self.metadata_path)

    def validate(self) -> None:
        if not os.path.isfile(self.sdr_path):
            raise FileNotFoundError(f"Sdr image not found: {self.sdr_path}")
        if not os.path.isfile(self.sdr_ev_path):
            raise FileNotFoundError(f"Sdr ev image not found: {self.sdr_ev_path}")
        if not (-5.01 < self.ev < 5.01):
            raise ValueError(f"EV value must be in [-5,5]")

        base_path, _ = os.path.splitext(self.sdr_path)
        if self.uhdr_path is None:
            self.uhdr_path = f"{base_path}_uhdr.jpg"
        if self.gainmap_path is None:
            self.gainmap_path = f"{base_path}_gainMap.jpg"
        if self.metadata_path is None:
            self.metadata_path = f"{base_path}_metadata.cfg"
