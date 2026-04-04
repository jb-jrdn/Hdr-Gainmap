import os
import numpy as np
from PIL import Image
from PIL.ImageCms import ImageCmsProfile
from io import BytesIO
import colour

CICP = {
    "primaries": {
        1: "sRGB",
        4: "ITU-R BT.470 - 525",
        5: "ITU-R BT.470 - 625",
        6: "NTSC (1987)",
        8: "Generic with C illuminant",
        9: "ITU-R BT.2020",
        10: "SMPTE ST 428",
        11: "SMPTE RP 431",
        12: "Display P3",
    },
    "cctf": {
        1: "ITU-R BT.709",
        6: "ITU-R BT.709",
        13: "sRGB",
        14: "ITU-R BT.709",
        15: "ITU-R BT.709",
        16: "ITU-R BT.2100 PQ",
        18: "ITU-R BT.2100 HLG",
    },
    "matrix": {
        0: "R'G'B'",
        1: "Y'CbCr (Rec. 709)",
        5: "Y'CbCr (Rec. 601)",
        6: "Y'CbCr (Rec. 601)",
        9: "Y'CbCr (Rec. 2020)",
        14: "ICtCp",
    },
}


def get_hdr_rgb_colourspace(
    primaries: str,  # typically "sRGB", "Display P3" or "ITU-R BT.2020"
    cctf: str,       # typically "ITU-R BT.2100 PQ" or "ITU-R BT.2100 HLG"
) -> colour.RGB_Colourspace:
    rgb_colourspace = colour.RGB_COLOURSPACES[primaries].copy()
    rgb_colourspace.cctf_encoding = colour.CCTF_ENCODINGS[cctf]
    rgb_colourspace.cctf_decoding = colour.CCTF_DECODINGS[cctf]
    rgb_colourspace.name = f"{primaries} - {cctf}"
    return rgb_colourspace


def open_hdr_avif_image(
    image_path: str,
) -> tuple[np.ndarray, colour.RGB_Colourspace]:
    """
    Return float np.ndarray image from avif file
    ----------
    image_path: path to 16bits HDR Avif image
    :return: tuple of numpy array with RGB values between 0 and 1 and hdr image color space info
    """
    try:
        import pillow_heif
    except ImportError:
        print(
            "⚠️ To open Avif files, please install pillow-heif -> \
            'python -m pip install pillow-heif'"
        )
        return

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image_pil = pillow_heif.open_heif(image_path, convert_hdr_to_8bit=False)

    if "16" not in image_pil.mode:
        print("Wrong hdr image format")
        return

    tcIn = image_pil.info.get("nclx_profile").get("transfer_characteristics")
    primIn = image_pil.info.get("nclx_profile").get("color_primaries")

    cctf = CICP["cctf"].get(tcIn) if tcIn else None
    primaries = CICP["primaries"].get(primIn) if primIn else None

    if primaries and cctf:
        colourspace = get_hdr_rgb_colourspace(primaries, cctf).copy()
    else:
        colourspace = None

    return np.asarray(image_pil) / (2**16 - 1), colourspace


def get_rgb_colourspace_from_icc_profile(
    image: Image,
) -> colour.RGB_Colourspace:
    """
    Extract the ICC profile from a Pillow image and return a corresponding
    colour-science RGB colourspace.

    Args:
        image (PIL.Image): Input image.

    Returns:
        colour.RGB_Colourspace: Detected colourspace or sRGB fallback.
    """
    icc_in = image.info.get("icc_profile")
    profileData = None
    try:
        f = BytesIO(icc_in)
        profileData = ImageCmsProfile(f)
    except:
        print("⚠️ Color profile not found: sRGB used")
        return colour.RGB_COLOURSPACES["sRGB"]

    profildescription = profileData.profile.profile_description

    colorspaceName = "sRGB"
    if "P3" in profildescription:
        if "sRGB" in profildescription or "Display P3" in profildescription:
            colorspaceName = "Display P3"
        else:
            colorspaceName = "DCI-P3"
    elif "2020" in profildescription:
        colorspaceName = "ITU-R BT.2020"
    elif "Adobe" in profildescription:
        colorspaceName = "Adobe RGB (1998)"
    elif "ProPhoto" in profildescription:
        colorspaceName = "ProPhoto RGB"

    return colour.RGB_COLOURSPACES[colorspaceName]


def open_sdr_image(
    image_path: str,
) -> tuple[np.ndarray, colour.RGB_Colourspace]:

    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image_pil = Image.open(image_path)
    if image_pil is None:
        print(f"Error: Could not open or decode the image at {image_path}")
        return None
    
    colourspace = get_rgb_colourspace_from_icc_profile(image_pil)
    image_np = np.array(image_pil) / 255

    return image_np, colourspace


def get_linear_image(
    image: np.ndarray,
    rgb_profile: colour.RGB_Colourspace,
    is_hdr: bool = False,
) -> np.ndarray:
    ratio = 1 if not is_hdr else 203
    return rgb_profile.cctf_decoding(image) / ratio


def get_adapted_rgb_primaries(
    image: np.ndarray,
    origin_rgb_profile: colour.RGB_Colourspace,
    new_rgb_profile: colour.RGB_Colourspace,
    is_hdr: bool = False,
):
    dest_image = colour.RGB_to_RGB(
        RGB=image,
        input_colourspace=origin_rgb_profile,
        output_colourspace=new_rgb_profile,
        chromatic_adaptation_transform="Bradford",
    )
    max_value = 1.0 if not is_hdr else None
    return np.clip(dest_image, 0, max_value)


def get_hdr_from_sdr_stacking(
    sdr_np_linear: np.ndarray,
    sdr_rgb_profile: colour.RGB_Colourspace,
    sdr_ev_np_linear: np.ndarray,
    sdr_ev_rgb_profile: colour.RGB_Colourspace,
    ev: float,
    luminance_mask_parameters: tuple = (0.25, 0.60),
    color_mask_parameters: tuple = (0.10, 0.25),
):
    # convert sdr_ev to sdr color space and apply ev
    sdr_ev_np_linear = colour.RGB_to_RGB(
        RGB=sdr_ev_np_linear,
        input_colourspace=sdr_ev_rgb_profile,
        output_colourspace=sdr_rgb_profile
    )
    sdr_ev_np_linear = np.clip(sdr_ev_np_linear, 0, 1)

    # split luma and chroma
    sdr_xyz = colour.RGB_to_XYZ(
        RGB=sdr_np_linear,
        colourspace=sdr_rgb_profile,
    )
    sdr_y = sdr_xyz[:,:,1]
    sdr_xy = colour.XYZ_to_xy(sdr_xyz)

    sdr_ev_xyz = colour.RGB_to_XYZ(
        RGB=sdr_ev_np_linear,
        colourspace=sdr_ev_rgb_profile,
    )
    sdr_ev_y = sdr_ev_xyz[:,:,1]
    sdr_ev_xy = colour.XYZ_to_xy(sdr_ev_xyz)

    def getMask(
        image: np.ndarray,
        mask_parameters: tuple[float, float],
    ) -> np.ndarray:
        mask_coef = 1 / (mask_parameters[1] - mask_parameters[0])
        mask_offset = - mask_coef * mask_parameters[0]
        return np.clip(image * mask_coef + mask_offset, 0, 1)

    # create masks
    luminance_mask = getMask(sdr_y, luminance_mask_parameters)
    color_mask = getMask(sdr_y, color_mask_parameters)
    color_mask = np.stack((color_mask,color_mask), axis=-1)

    # hdr luminance
    hdr_y = sdr_y * (1-luminance_mask) + sdr_ev_y * (2**ev) * luminance_mask

    # hdr color
    hdr_xy = sdr_xy * (1-color_mask) + sdr_ev_xy * color_mask

    # merge luma and chroma
    hdr_xyy = np.zeros_like(sdr_xyz)
    hdr_xyy[:,:,0:2] = hdr_xy[:,:]
    hdr_xyy[:,:,2] = hdr_y[:,:]
    hdr_xyz = colour.xyY_to_XYZ(hdr_xyy)
    hdr_np_linear = colour.XYZ_to_RGB(
        XYZ=hdr_xyz,
        colourspace=sdr_rgb_profile,
    )

    return hdr_np_linear
