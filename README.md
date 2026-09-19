# 📷 Vidyamandira Photo Watermarker (RKMVPC)

![Version](https://img.shields.io/badge/version-3.6.0%20(Beta)-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

A modern, desktop watermarking application custom-built for the **Vidyamandira Photography Club (RKMVPC)**. Designed for batch watermarking, single-photo editing, EXIF metadata preservation, and preparing high-resolution photos for publication.

---

### 📥 Quick Download

[![Download Latest Release v3.6.0 (Beta)](https://img.shields.io/badge/Download-RKMVPC__Beta.exe%20(v3.6.0%20Beta)-17B978?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/RKMVPC_Beta.exe)

> **Note:** Click the button above to directly download the latest standalone executable (`RKMVPC_Beta.exe` v3.6.0 Beta). No Python installation required!

---

## 🚀 What's New in v3.6.0 (Beta)

* 🖱️ **Interactive Canvas Drag-and-Drop:** Click on any watermark element (logos, QR code, copyright text) directly on the live preview canvas and freely drag & drop it anywhere on the image with real-time feedback.
* 🎚️ **Blender-Style Draggable Numeric Scrub Fields:**
  * Replaced position dropdowns and sliders with sleek draggable number fields (`↔ Pos X`, `↕ Pos Y`).
  * **Click & Drag:** Drag horizontally left/right to smoothly scrub and adjust values.
  * **Shift + Drag / Scroll:** Hold <kbd>Shift</kbd> for fine-grained precision adjustments.
  * **Mouse Wheel:** Scroll over any numeric field to increment/decrement values.
  * **Double-Click to Type:** Double-click on any field to type exact percentages or numbers directly.
  * **Bi-directional Visual Fill Bars:** Real-time progress bars indicating offset relative to center.
* 🛡️ **Photo Boundary Clamping:** Watermark elements are strictly confined within the photo area, stopping seamlessly at the inner edge without bleeding into the white border frame.
* 🎯 **Centered Default Placement:** All newly added elements default to the center of the image without confusing position dropdowns.
* © **Smart Copyright Defaults:** Copyright watermark automatically defaults to the bottom-left corner with a contrasting background box enabled out-of-the-box.
* ⌨️ **Configurable Arrow Key Nudge:** Use arrow keys (<kbd>↑</kbd> <kbd>↓</kbd> <kbd>←</kbd> <kbd>→</kbd>) for pixel-perfect nudging on the canvas (configurable in `production.py`).

---

## 📦 Version History & Downloads

All current and past versions of the executable are available in the repository's [`dist/`](file:///c:/Users/manas/Documents/codes/python_projects/projects/RKMVPC-Watermark/dist) directory for testing and archive access:

| Version | Executable | Highlights & Changes | Download |
| :--- | :--- | :--- | :--- |
| **v3.6.0 (Beta)** *(Latest)* | `RKMVPC_Beta.exe` | Interactive canvas drag-and-drop, Blender-style draggable numeric scrub fields, photo boundary clamping, centered default placement, and auto bottom-left copyright box. | [📥 Download v3.6.0 Beta](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/RKMVPC_Beta.exe) |
| **v3.5.0** | `RKMVPC.exe` | Complete UI redesign, sidebar navigation, scrollable controls, live slider badges, spontaneous mouse-wheel canvas scaling & deferred single-image save destination. | [📥 Download v3.5.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/RKMVPC.exe) |
| **v3.1.0** | `watermark V3.1.exe` | Enhanced preview calculations, text rotation support, and background bounding box controls. | [📥 Download v3.1](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermark%20V3.1.exe) |
| **v3.0.0** | `watermark V3.exe` | Added dark mode startup splash dialog, card selection layout, and relative resolution scaling. | [📥 Download v3.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermark%20V3.exe) |
| **v2.8.0** | `watermard_V2-8.exe` | Improved batch image export pipeline, progress bar with ETA countdown. | [📥 Download v2.8](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermard_V2-8.exe) |
| **v2.0.0** | `watermard_V2-0.exe` | Multi-element support (RKM logo, Club logo, QR code, Copyright text). | [📥 Download v2.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermard_V2-0.exe) |
| **v1.0.0** | `watermark.exe` | Initial release with basic single-logo overlay and batch processing. | [📥 Download v1.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermark.exe) |

---

## ✨ Features

* **🗂 Dual Workflow Modes:**
  * **Batch Folder Mode:** Watermark an entire directory of photos at once with automated output naming (`*_watermarked`).
  * **Single Image Mode:** Focus on a single photo with full preview. Destination folder selection is deferred until you click **"Save / Export Image"**.
* **🎨 Modern UI Design:**
  * **Left Sidebar Navigation:** Quickly switch between Master Settings, RKM Logo, Club Logo, QR Code, Copyright, and Custom Text.
  * **Scrollable Control Panel:** Card-grouped controls that automatically adapt without getting cut off on lower-resolution screens.
  * **Blender-Style Scrub Fields:** Draggable, scrollable, and double-clickable numeric fields.
* **🖱️ Live Preview Interactivity:**
  * Click & drag any watermark element directly on the preview canvas.
  * Hovering over any element on the preview canvas auto-selects it.
  * Mouse-wheel scrolling on the preview canvas scales elements spontaneously in real-time.
* **🖼️ Multiple Watermark Overlays:**
  * **RKM Logo** (Color & B&W version toggle)
  * **Photography Club Logo**
  * **QR Code**
  * **Copyright Information** (with rotation, custom font, and background box)
  * **Custom Text Watermark**
* **📐 Resolution-Independent Scaling:** Watermark dimensions and border padding adapt proportionally based on the geometric mean of each photo, ensuring identical visual proportions across different camera resolutions.
* **📸 Metadata Preservation:** Keeps EXIF camera data and ICC color profiles intact upon export.

---

## 🛠️ Requirements & Run from Source

If you want to run or modify the Python source code directly:

### Prerequisites
- Python **3.8+**
- Pillow (`PIL`)
- Tkinter (included with standard Python for Windows)

### Running Locally
```bash
# Clone the repository
git clone https://github.com/ManaswiDutta/RKMVPC-Watermark.git
cd RKMVPC-Watermark

# Install dependencies
pip install Pillow

# Run application
python production.py
```

---

## 🏗️ Building Executables (PyInstaller)

To build a standalone `.exe` from source:

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --noconfirm --onefile --windowed --name RKMVPC_Beta --icon logo.ico --version-file file_version_info.txt --add-data "rkm_logo.png;." --add-data "bnw_rkm_logo.png;." --add-data "logo.png;." --add-data "qr.jpeg;." production.py
```

The output executable will be generated at `dist/RKMVPC_Beta.exe`.

---

## 📄 License

<<<<<<< Updated upstream
This project is maintained by **Tech Society of Vidyamandira** for the **Photography Club**. Distributed under the [MIT License](LICENSE).
=======
This project is maintained by the **Vidyamandira Photography Club**. Distributed under the [MIT License](LICENSE).

>>>>>>> Stashed changes
