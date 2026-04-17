import os
from tools.uhdr import UltraHdr
from tools import image_tools
from tools.preset import Preset
from tools.image_settings import PRESETS


class SdrHdrToUhdr:

    def __init__(
        self,
        sdr_path: str,
        hdr_path: str,
        uhdr_path: str | None = None,
        preset: str = Preset.default,
        tag: bool = False,
        keep_temp_files: bool = False,
    ) -> None:
        self.sdr_path = sdr_path
        self.hdr_path = hdr_path
        self.uhdr_path = uhdr_path
        self.settings = PRESETS[preset]
        self.tag = tag
        self.keep_temp_files = keep_temp_files
        self.sdr_changed = False

    def run(self) -> None:
        # load images
        sdr_np_image, sdr_rgb_profile = image_tools.open_sdr_image(self.sdr_path)
        hdr_np_image, hdr_rgb_profile = image_tools.open_hdr_avif_image(self.hdr_path)

        # check sizes consistency
        if sdr_np_image.shape[:2] != hdr_np_image.shape[:2]:
            raise("Sdr and Hdr image sizes are not identical")

        # Crop to respect ratio if needed
        if self.settings.min_ratio_w_h or self.settings.max_ratio_w_h:
            sdr_np_image = image_tools.crop_to_ratio(
                img=sdr_np_image,
                min_ratio=self.settings.min_ratio_w_h,
                max_ratio=self.settings.max_ratio_w_h,
            )
            hdr_np_image = image_tools.crop_to_ratio(
                img=hdr_np_image,
                min_ratio=self.settings.min_ratio_w_h,
                max_ratio=self.settings.max_ratio_w_h,
            )
            self.sdr_changed = True
        
        # Resize to respect max size if needed
        if self.settings.width_max or self.settings.height_max:
            sdr_np_image = image_tools.resize_to_max(
                img=sdr_np_image,
                width_max=self.settings.width_max,
                height_max=self.settings.height_max,
            )
            hdr_np_image = image_tools.resize_to_max(
                img=hdr_np_image,
                width_max=self.settings.width_max,
                height_max=self.settings.height_max,
            )
            self.sdr_changed = True

        # get rgb linear values
        sdr_np_image_linear = image_tools.get_linear_image(
            image=sdr_np_image,
            rgb_profile=sdr_rgb_profile,
        )
        hdr_np_image_linear = image_tools.get_linear_image(
            image=hdr_np_image,
            rgb_profile=hdr_rgb_profile,
            is_hdr=True,
        )

        # convert hdr values to the sdr color profile
        hdr_np_image_linear = image_tools.get_adapted_rgb_primaries(
            image=hdr_np_image_linear,
            origin_rgb_profile=hdr_rgb_profile,
            new_rgb_profile=sdr_rgb_profile,
            is_hdr=True,
        )

        # Add Hdr tag if asked
        if self.tag:
            image_tools.add_hdr_tag(
                sdr_np_image_linear=sdr_np_image_linear,
                hdr_np_image_linear=hdr_np_image_linear,
            )
            self.sdr_changed = True
        
        # Save new sdr if needed
        sdr_path = self.sdr_path
        if self.sdr_changed:
            base_path, _ = os.path.splitext(self.sdr_path)
            sdr_path = f"{base_path}_new.jpg"
            # TODO: rgb profil management
            image_tools.save_sdr_image(
                sdr_np_image_linear=sdr_np_image_linear,
                rgb_profile=sdr_rgb_profile,
                sdr_path=sdr_path,
                icc_path="data/DisplayP3.icc",
            )

        # create uhdr image
        if not self.uhdr_path:
            base_path, _ = os.path.splitext(self.sdr_path)
            self.uhdr_path = f"{base_path}_uhdr.jpg"
        ultra_hdr = UltraHdr(
            linear_sdr_image=sdr_np_image_linear,
            linear_hdr_image=hdr_np_image_linear,
            input_sdr_path=sdr_path,
            output_uhdr_path=self.uhdr_path,
            settings=self.settings.uhdr_settings,
            keep_temp_files=self.keep_temp_files,
        )
        ultra_hdr.run()

        # delete temp file if needed
        if self.tag and not self.keep_temp_files:
            os.remove(sdr_path)

    def validate(self) -> None:
        if not os.path.isfile(self.sdr_path):
            raise FileNotFoundError(f"Sdr image not found: {self.sdr_path}")
        if not os.path.isfile(self.hdr_path):
            raise FileNotFoundError(f"Hdr image file not found: {self.hdr_path}")


def process_folder(
    input_directory: str,
    overwrite_existing: bool = False,
    keep_temp_files: bool = False,
) -> None:
    """
    Processes all JPG images in the specified directory to generate UHDR images.
    For each JPG file, if a corresponding AVIF file exists, generates a UHDR image.
    Skips processing if the UHDR output already exists and `overwrite_existing` is False.

    Args:
        input_directory: Path to the directory containing JPG and AVIF files.
        overwrite_existing: If True, overwrites existing UHDR files. Defaults to False.
        keep_temporary_files: If True, retains temporary files after processing. Defaults to False.

    Raises:
        FileNotFoundError: If "input_directory" does not exist or is not a directory.
        ValueError: If no valid JPG/AVIF pairs are found in the directory.
    """
    if not os.path.isdir(input_directory):
        raise FileNotFoundError(f"Directory does not exist: {input_directory}")

    file_list= os.listdir(input_directory)

    for filename in file_list:
        base_name, file_extension = os.path.splitext(filename)

        uhdr_output_filepath = os.path.join(input_directory, f"{base_name}_uhdr.jpg")
        if not overwrite_existing and os.path.isfile(uhdr_output_filepath):
            continue

        if file_extension.lower() == ".jpg":
            corresponding_avif_filepath = os.path.join(input_directory, f"{base_name}.avif")

            if os.path.isfile(corresponding_avif_filepath):
                print(f"Processing file: {filename}")
                process = SdrHdrToUhdr(
                    sdr_path=os.path.join(input_directory, filename),
                    hdr_path=corresponding_avif_filepath,
                    keep_temp_files=keep_temp_files,
                )
                process.validate()
                process.run()
