import os
import subprocess
import numpy as np
import cv2
from uhdr.uhdr_metadata import UhdrMetadata
from uhdr.uhdr_settings import UhdrSettings


ULTRAHDR_APP = r"ultrahdr_app"


class UltraHdr:

    def __init__(
        self,
        linear_sdr_image: np.ndarray,
        linear_hdr_image: np.ndarray,
        input_sdr_path: str,
        output_uhdr_path: str | None = None,
        settings: UhdrSettings = UhdrSettings(),
        metadata: UhdrMetadata = UhdrMetadata(),
        keep_temp_files: bool = False,
    ):
        self.linear_sdr_image = linear_sdr_image
        self.linear_hdr_image = linear_hdr_image
        self.sdr_path = input_sdr_path
        self.uhdr_path = output_uhdr_path
        self.settings = settings
        self.metadata = metadata
        self.keep_temp_files = keep_temp_files

        base_path, _ = os.path.splitext(self.sdr_path)
        self.gainmap_path = f"{base_path}_gainMap.jpg"
        self.metadata_path = f"{base_path}_metadata.cfg"
        if not self.uhdr_path:
            self.uhdr_path = f"{base_path}_uhdr.jpg"
    
    def run(self) -> None:
        # process gain map
        gainmap_np_image, min_map, max_map = UltraHdr.get_gainmap(
            sdr_np_image_linear=self.linear_sdr_image,
            hdr_np_image_linear=self.linear_hdr_image,
            metadata=self.metadata,
            min_gain=self.settings.min_gain,
            max_gain=self.settings.max_gain,
        )

        # save gain map
        UltraHdr.write_gainmap(
            gainmap=gainmap_np_image,
            gainmap_path=self.gainmap_path,
            quality=self.settings.gain_map_quality,
            size_factor=self.settings.gain_map_size_factor,
        )
        
        # create metadata file
        self.metadata.min_content_boost = min_map
        self.metadata.max_content_boost = max_map
        UltraHdr.create_metadata(
            metadata=self.metadata,
            metadata_path=self.metadata_path,
        )

        # create uhdr image with ultrahdr_app
        UltraHdr.create_uhdr_image_from_sdr_and_gainmap(
            sdr_path=self.sdr_path,
            gainmap_path=self.gainmap_path,
            metadata_path=self.metadata_path,
            output_uhdr_path=self.uhdr_path,
        )

        # delete temp files if needed
        if not self.keep_temp_files:
            os.remove(self.gainmap_path)
            os.remove(self.metadata_path)

    @staticmethod
    def create_metadata(
        metadata_path: str,
        metadata: UhdrMetadata,
    ) -> None:
        """
        Generate a metadata configuration file for Ultra HDR gain maps.

        Args:
            metadata_path: Destination path for the metadata file (e.g., "metadata.cfg").
            metadata: UhdrMetadata dataclass containing metadata parameters.

        Raises:
            ValueError: If metadata is not valid.
            IOError: If the file cannot be written.
        """
        if not metadata.is_valid():
            raise ValueError("Metadata is not valid.")

        used_max_hdr_capacity = max(min(metadata.max_hdr_capacity, metadata.max_content_boost), 1.1)

        content_lines = [
            f"--minContentBoost {metadata.min_content_boost:.3f}",
            f"--maxContentBoost {metadata.max_content_boost:.3f}",
            f"--gamma {metadata.gamma:.3f}",
            f"--offsetSdr {metadata.sdr_offset:.6f}",
            f"--offsetHdr {metadata.hdr_offset:.6f}",
            f"--hdrCapacityMin {metadata.min_hdr_capacity:.3f}",
            f"--hdrCapacityMax {used_max_hdr_capacity:.3f}",
            f"--useBaseColorSpace {metadata.use_base_color_space}",
        ]
        content = "\n".join(content_lines)

        try:
            with open(metadata_path, 'w', encoding='utf-8') as file:
                file.write(content)
        except IOError as e:
            raise IOError(f"Failed to write metadata file: {e}")

    @staticmethod
    def get_gainmap(
        sdr_np_image_linear: np.ndarray,
        hdr_np_image_linear: np.ndarray,
        metadata: UhdrMetadata,
        min_gain: float = 0.8,
        max_gain: float = 10000/203,
    ) -> tuple[np.ndarray, float, float]:
        """
        Get Ultra HDR gainmap from linear SDR and HDR images.

        Args:
            sdr_np_image_linear: Linear SDR image [0-1].
            hdr_np_image_linear: Linear HDR image (1 is the SDR white level).
            metadata: Metadata used to compute the gainmap.
            min_gain: Minimum gain value.
            max_gain: Maximum gain value.

        Returns:
            tuple[np.ndarray, float, float]: gainmap, min_content_boost, max_content_boost

        Raises:
            ValueError: If input images have different shapes.
        """
        if sdr_np_image_linear.shape != hdr_np_image_linear.shape:
            raise ValueError("SDR and HDR images must have the same shape.")

        gain = (hdr_np_image_linear + metadata.hdr_offset) / (sdr_np_image_linear + metadata.sdr_offset)

        gain = UltraHdr.get_optimized_gain(gain)

        min_content_boost = np.clip(np.min(gain), min_gain, max_gain)
        max_content_boost = np.clip(np.max(gain), min_gain, max_gain)

        min_map_log2 = np.log2(min_content_boost)
        max_map_log2 = np.log2(max_content_boost)

        print(f"min gain: {min_content_boost:.2f}x -> {min_map_log2:.2f} ev")
        print(f"max gain: {max_content_boost:.2f}x -> {max_map_log2:.2f} ev")

        log_recovery = (np.log2(gain) - min_map_log2) / (max_map_log2 - min_map_log2)
        clamped_recovery = np.clip(log_recovery, 0.0, 1.0)
        recovery = np.power(clamped_recovery, metadata.gamma)
        gainmap = np.round(recovery * 255).astype(np.uint8)
        return gainmap, min_content_boost, max_content_boost

    @staticmethod
    def get_optimized_gain(
        gain: np.ndarray,
        percentile: float = 99.998,
    ) -> np.ndarray:
        """
        Reduce higher gain value to avoid headroom compression when gain map is applied, based on max value.
        Produce slighlty lower high values (difficult to see), but better global luminance of HDR image.
        Usefull when dead pixels are in the image.
        Chromaticity preserved.
        """
        max_rgb = np.max(gain, axis=-1)

        p_low = np.percentile(max_rgb, percentile - 0.01)
        p_high = np.percentile(max_rgb, percentile)
        gmax = max_rgb.max()

        print(f"optim param -> max: {gmax:.2f} | p_low: {p_low:.2f} | p_high: {p_high:.2f}")

        eps = 1e-8
        scale = (p_high - p_low) / (gmax - p_low + eps)

        mapped = max_rgb.copy()
        mask = mapped > p_low
        mapped[mask] = p_low + (mapped[mask] - p_low) * scale

        ratio = mapped / (max_rgb + eps)

        optimized_gain = gain * ratio[..., None]
        return optimized_gain

    @staticmethod
    def write_gainmap(
        gainmap: np.ndarray,
        gainmap_path: str,
        quality: int = 90,
        size_factor: int = 1,
    ) -> None:
        """
        Write a gainmap image to disk in JPEG format.

        Args:
            gainmap: Gainmap image as a numpy array (uint8, RGB format).
            gainmap_path: Destination path for the gainmap image.
            quality: JPEG quality (0-100). Best 100, worst 0, default 90.
            size_factor: gainmap size. Best 1, worst 128, default 1.

        Raises:
            IOError: If writing the file fails.
        """
        try:
            if size_factor != 1:
                height, width = gainmap.shape[:2]
                gainmap = cv2.resize(gainmap, (width // size_factor, height // size_factor))
            success = cv2.imwrite(
                gainmap_path,
                cv2.cvtColor(gainmap, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_JPEG_QUALITY, quality],
            )
            if not success:
                raise IOError(f"Failed to write gainmap to {gainmap_path}.")
        except Exception as e:
            raise IOError(f"Error writing gainmap: {e}")

    @staticmethod
    def create_uhdr_image_from_sdr_and_gainmap(
        sdr_path: str,
        gainmap_path: str,
        metadata_path: str,
        output_uhdr_path: str | None = None,
    ) -> str:
        """
        Generates a UHDR image from an SDR image, gainmap, and metadata.

        Args:
            sdr_path: Path to the input SDR image.
            gainmap_path: Path to the gainmap image.
            metadata_path: Path to the metadata file.
            output_uhdr_path: Output path for the generated UHDR image. If None, a default path is constructed.

        Returns:
            str: Path to the generated UHDR image.

        Raises:
            FileNotFoundError: If input files are not found.
            ValueError: If quality values are invalid.
            RuntimeError: If the subprocess command fails.
        """

        # checks
        if not os.path.exists(sdr_path):
            raise FileNotFoundError(f"SDR image not found: {sdr_path}")
        if not os.path.exists(gainmap_path):
            raise FileNotFoundError(f"Gain map not found: {gainmap_path}")
        if not os.path.exists(metadata_path):
            raise FileNotFoundError(f"Metadata not found: {metadata_path}")

        uhdr_path = output_uhdr_path or f"{os.path.splitext(sdr_path)[0]}_uhdr.jpg"
        command = [
            ULTRAHDR_APP,
            "-m", "0",
            "-i", sdr_path,
            "-g", gainmap_path,
            "-f", metadata_path,
            "-z", uhdr_path,
        ]

        try:
            subprocess.run(command, check=True)
            print(f"Process completed successfully: {uhdr_path}")
        except subprocess.CalledProcessError as e:
            print(f"Return code: {e.returncode}")
            raise RuntimeError(f"Command failed: {e}") from e
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise

        return uhdr_path

    @staticmethod
    def create_uhdr_image_from_sdr_and_hdr_data(
        sdr_np_image_linear: np.ndarray,
        hdr_np_image_linear: np.ndarray,
        sdr_path: str,
        metadata: UhdrMetadata = UhdrMetadata(),
        gainmap_path: str | None = None,
        metadata_path: str | None = None,
        output_uhdr_path: str | None = None,
        keep_temp_files: bool = False,
    ) -> str:
        base_path, _ = os.path.splitext(sdr_path)
        if output_uhdr_path is None:
            output_uhdr_path = f"{base_path}_uhdr.jpg"
        if gainmap_path is None:
            gainmap_path = f"{base_path}_gainMap.jpg"
        if metadata_path is None:
            metadata_path = f"{base_path}_metadata.cfg"

        # process gain map
        gainmap_np_image, min_map, max_map = UltraHdr.get_gainmap(
            sdr_np_image_linear=sdr_np_image_linear,
            hdr_np_image_linear=hdr_np_image_linear,
            metadata=metadata,
        )

        # save gain map
        UltraHdr.write_gainmap(
            gainmap=gainmap_np_image,
            gainmap_path=gainmap_path,
        )
        
        # create metadata file
        metadata.min_content_boost = min_map
        metadata.max_content_boost = max_map
        UltraHdr.create_metadata(
            metadata=metadata,
            metadata_path=metadata_path,
        )

        # create uhdr image with ultrahdr_app
        UltraHdr.create_uhdr_image_from_sdr_and_gainmap(
            sdr_path=sdr_path,
            gainmap_path=gainmap_path,
            metadata_path=metadata_path,
            output_uhdr_path=output_uhdr_path,
        )

        # delete temp files if needed
        if not keep_temp_files:
            os.remove(gainmap_path)
            os.remove(metadata_path)

        return output_uhdr_path
