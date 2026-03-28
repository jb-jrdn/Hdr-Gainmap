UhdrGen
========

Convert SDR + HDR images to Jpeg with gainmap.

Description
-----------
This project provides a Python tool to generate single HDR jpg with Gain map,
from SDR/HDR pair.

Lightroom does not provide precise control over the processing of both SDR and HDR images when using a gain map.
By combining an SDR image with an HDR image to create an Ultra HDR image with a gain map, you achieve an optimal balance across all types of displays, with fine-grained control over how each version is rendered.
In addition, the resulting HDR images are fully compatible with Instagram posts—something that is not always guaranteed with Lightroom exports.

Installation
------------
1. Clone the project:
```
   git clone https://github.com/jb-jrdn/UhdrGen.git
   cd UhdrGen
```

2. Create a virtual environment:
```
   python3 -m venv venv
   source venv/bin/activate    # macOS / Linux
   venv\Scripts\activate       # Windows PowerShell
```

3. Install dependencies:
```
   pip install -r requirements.txt
```

4. Install ultrahdr_app:
 - macOS (using Homebrew):
```
        brew install libultrahdr
```
- Windows: Install or build app from https://github.com/google/libultrahdr, and add 'ultrahdr_app' to the PATH

Usage
-----
Single file mode:
```
   python main.py --sdr path/to/image_sdr.jpg --hdr path/to/image_hdr.avif --output path/to/output.jpg
```

Batch mode (entire folder):
- SDR and HDR images must share the same base name with suffixes `_sdr` / `_hdr`:
    image1_sdr.jpg / image1_hdr.avif
    image2_sdr.jpg / image2_hdr.avif
```
   python main.py --dir path/to/images/
```

Optimal Lightroom settings for Instagram post:
- SDR image:
   - HDR Off in Develop mode
   - Export setting:
      - Image Format: JPEG
      - Quality: 95 (recommended)
      - Color Space: Display P3
      - HDR Output: No
- HDR image:
   - HDR On in Develop mode
   - Export setting:
      - Image Format: AVIF
      - Quality: 100
      - Color Space: HDR P3
      - HDR Output: Yes
      - Maximize Compatibility: No
Note:
   - SDR and HDR images must have the same image size
   - To use batch mode of this tool, export SDR and HDR in the same folder

