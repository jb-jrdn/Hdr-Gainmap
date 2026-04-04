import os
from tools import uhdr_tools, image_tools

class SdrHdrToUhdr:

    def __init__(
        self,
        sdr_path: str,
        hdr_path: str,
        uhdr_path: str | None = None,
        keep_temp_files: bool = False,
    ) -> None:
        self.sdr_path = sdr_path
        self.sdr_np_image = None
        self.sdr_rgb_profile = None

        self.hdr_path = hdr_path
        self.hdr_np_image = None
        self.hdr_rgb_profile = None

        self.uhdr_path = uhdr_path

        self.gainmap_path = None
        self.gainmap_np_image = None

        self.metadata_path = None
        self.metadata = uhdr_tools.UhdrMetadata()

        self.keep_temp_files = keep_temp_files

    def run(self) -> None:
        # load images
        self.sdr_np_image, self.sdr_rgb_profile = image_tools.open_sdr_image(self.sdr_path)
        self.hdr_np_image, self.hdr_rgb_profile = image_tools.open_hdr_avif_image(self.hdr_path)

        # get rgb linear values
        sdr_np_image_linear = image_tools.get_linear_image(self.sdr_np_image, self.sdr_rgb_profile)
        hdr_np_image_linear = image_tools.get_linear_image(self.hdr_np_image, self.hdr_rgb_profile, is_hdr=True)

        # convert hdr values to the sdr color profile
        hdr_np_image_linear = image_tools.get_adapted_rgb_primaries(
            image=hdr_np_image_linear,
            origin_rgb_profile=self.hdr_rgb_profile,
            new_rgb_profile=self.sdr_rgb_profile,
            is_hdr=True,
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
        if not os.path.isfile(self.hdr_path):
            raise FileNotFoundError(f"Hdr image file not found: {self.hdr_path}")

        base_path, _ = os.path.splitext(self.sdr_path)
        if self.uhdr_path is None:
            self.uhdr_path = f"{base_path}_uhdr.jpg"
        if self.gainmap_path is None:
            self.gainmap_path = f"{base_path}_gainMap.jpg"
        if self.metadata_path is None:
            self.metadata_path = f"{base_path}_metadata.cfg"


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