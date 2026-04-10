Hdr-Gainmap
=======

Generate HDR images (jpeg + Gain Map) optimized for SDR and HDR displays.

Overview
-----------

This project is a Python tool that creates Ultra HDR images by combining SDR and HDR sources into a single JPEG file with a gain map.

This ensures:

- ✅ Optimal rendering on SDR screens
- ✅ Enhanced brightness and contrast on HDR displays
- ✅ Compatibility with platforms like Instagram

Quick Start
------------------

```
   git clone https://github.com/jb-jrdn/Hdr-Gainmap
   cd Hdr-Gainmap

   python3 -m venv venv
   source venv/bin/activate    # macOS / Linux
   # venv\Scripts\activate     # Windows PowerShell

   pip install -r requirements.txt
```

<h3>Install UltraHDR library</h3>

- macOS:

```
brew install libultrahdr
```

- Windows:

Install from https://github.com/google/libultrahdr <br>
Add 'ultrahdr_app' to the PATH

Usage
--------

<h3>SDR + HDR → UltraHDR (✅ Recommended)</h3>

Combine SDR image (jpg) and HDR image (avif)

```
main.py --sdr input_sdr.jpg --hdr input_hdr.avif -o output_uhdr_1.jpg
```

<table>
  <tr>
    <td><b>SDR image</b></br><small>input_sdr.jpg</small></td>
    <td><b>HDR image</b></br><small>input_hdr.avif</small></td>
    <td><b>HDR image with gain map</b></br><small>output_uhdr_1.jpg</small></td>
  </tr>
  <tr>
    <td><img src="samples/input_sdr.jpg" width="250"/></td>
    <td><img src="samples/input_hdr.avif" width="250"/></td>
    <td><img src="samples/output_uhdr_1.jpg" width="250"/></td>
  </tr>
</table>

<h4>Batch mode:</h4>

```
main.py --dir path/to/images/
```

File naming convention type:

```
image.jpg
image.avif
```

---

<h3>SDR + SDR -xEV → UltraHDR</h3>

Combine SDR image and SDR underexposed image (with EV value)

```
main.py --sdr input_sdr.jpg --sdrev input_sdr_2ev.avif --ev 2 -o output_uhdr_2.jpg
```

<table>
  <tr>
    <td><b>SDR image</b></br><small>input_sdr.jpg</small></td>
    <td><b>SDR image - 2EV</b></br><small>input_sdr_2ev.avif</small></td>
    <td><b>HDR image with gain map</b></br><small>output_uhdr_2.jpg</small></td>
  </tr>
  <tr>
    <td><img src="samples/input_sdr.jpg" width="250"/></td>
    <td><img src="samples/input_sdr_2ev.jpg" width="250"/></td>
    <td><img src="samples/output_uhdr_2.jpg" width="250"/></td>
  </tr>
</table>

---

<h3>SDR boosted EV → UltraHDR</h3>

Generate HDR from one SDR image with exposure compensation

```
main.py --sdr input_sdr_2ev.jpg --ev 2 -o output_uhdr_3.jpg
```

<table>
  <tr>
    <td><b>SDR image</b></br><small>input_sdr_2ev.jpg</small></td>
    <td><b>HDR image with gain map</b></br><small>output_uhdr_3.jpg</small></td>
  </tr>
  <tr>
    <td><img src="samples/input_sdr_2ev.jpg" width="250"/></td>
    <td><img src="samples/output_uhdr_3.jpg" width="250"/></td>
  </tr>
</table>

Recommended Lightroom Export Settings
-------------------------------------
- SDR image:
   - HDR Off in Develop mode
   - Export setting:
      - Image Format: JPEG
      - Quality: 95
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

<h3>Note:</h3>

   - SDR and HDR images must have the same image size
   - To use batch mode of this tool, export SDR and HDR in the same folder

📄 License
----------

MIT
