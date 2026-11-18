# Third-party components

The MIT license in this repository covers the project's own source code. It does not replace the licenses of bundled runtimes, libraries or OCR model weights.

Windows bundles use Python/Tcl/Tk, RapidOCR and its packaged PaddleOCR-family models, ONNX Runtime, OpenCV, NumPy, Pillow, Shapely, pyclipper, OmegaConf, Requests and their dependencies. These components remain subject to their respective distribution licenses.

The Windows packaging script copies license and notice files supplied in installed distributions into the release's `Third Party Licenses` directory, and records package names and versions in `Installed Packages.txt`. Tcl/Tk license text shipped with the application is retained by the bundle. Please retain those files when redistributing the application.

Upstream projects:

- Python: https://www.python.org/
- Tcl/Tk: https://www.tcl-lang.org/
- RapidOCR: https://github.com/RapidAI/RapidOCR
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- ONNX Runtime: https://github.com/microsoft/onnxruntime
- OpenCV: https://github.com/opencv/opencv-python
- NumPy: https://numpy.org/
- Pillow: https://python-pillow.org/
- Shapely: https://github.com/shapely/shapely
- PyInstaller build tool and distribution exception: https://pyinstaller.org/en/stable/license.html
