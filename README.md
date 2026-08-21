# 📷 Vidyamandira Photo Watermarker (RKMVPC)

![Version](https://img.shields.io/badge/version-3.5.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-0078D4.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

A modern, desktop watermarking application custom-built for the **Vidyamandira Photography Club (RKMVPC)**. Designed for batch watermarking, single-photo editing, EXIF metadata preservation, and preparing high-resolution photos for publication.

---

### 📥 Quick Download

[![Download Latest Release v3.5.0](https://img.shields.io/badge/Download-RKMVPC.exe%20(v3.5.0)-17B978?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/RKMVPC.exe)

> **Note:** Click the button above to directly download the latest standalone executable (`RKMVPC.exe` v3.5.0). No Python installation required!

---

## 🚀 What's New in v3.5.0

* 🎨 **Complete Interface Redesign:** Sleek, modern dark-themed GUI organized with styled cards, teal headers, and responsive layouts.
* 🧭 **Vertical Sidebar Navigation:** Effortlessly switch between master options and individual watermark controls with active indicator states.
* 🗂 **Optimized Dual Workflows:**
  * **Batch Folder:** Process entire albums with real-time progress tracking and ETA calculations.
  * **Single-Image Editing:** Work with full-resolution previews and deferred destination selection (only prompted when clicking *Save / Export*).
* ⌨️ **Keyboard & Mouse Controls:**
  * **Arrow Keys (`↑`, `↓`, `←`, `→`):** Move and fine-tune watermark positions on screen with live slider and preview sync.
  * **Mouse-Wheel Scaling:** Hover over any logo or text on the canvas to auto-select and scale it spontaneously.
  * **`Esc` Key:** Instantly deselect elements and return to Master Settings.
* 📊 **Live Value Readouts:** Real-time percentage badges (`%`) and degree indicators (`°`) beside every slider.
* 🪟 **Window Lifecycle & Taskbar Integration:** Full Windows taskbar identity and clean process termination on close.

---

## 📦 Version History & Downloads

All current and past versions of the executable are available in the repository's [`dist/`](file:///c:/Users/manas/Documents/codes/python_projects/projects/RKMVPC-Watermark/dist) directory for testing and archive access:

| Version | Executable | Highlights & Changes | Download |
| :--- | :--- | :--- | :--- |
| **v3.5.0** *(Latest)* | `RKMVPC.exe` | Complete UI redesign, sidebar navigation, scrollable controls, live slider badges, spontaneous mouse-wheel canvas scaling & deferred single-image save destination. | [📥 Download v3.5.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/RKMVPC.exe) |
| **v3.1.0** | `watermark V3.1.exe` | Enhanced preview calculations, text rotation support, and background bounding box controls. | [📥 Download v3.1](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermark%20V3.1.exe) |
| **v3.0.0** | `watermark V3.exe` | Added dark mode startup splash dialog, card selection layout, and relative resolution scaling. | [📥 Download v3.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermark%20V3.exe) |
| **v2.8.0** | `watermard_V2-8.exe` | Improved batch image export pipeline, progress bar with ETA countdown. | [📥 Download v2.8](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermard_V2-8.exe) |
| **v2.0.0** | `watermard_V2-0.exe` | Multi-element support (RKM logo, Club logo, QR code, Copyright text). | [📥 Download v2.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermard_V2-0.exe) |
| **v1.0.0** | `watermark.exe` | Initial release with basic single-logo overlay and batch processing. | [📥 Download v1.0](https://github.com/ManaswiDutta/RKMVPC-Watermark/raw/main/dist/watermark.exe) |

---

## ✨ Features (v3.5.0)

* **🗂 Dual Workflow Modes:**
  * **Batch Folder Mode:** Watermark an entire directory of photos at once with automated output naming (`*_watermarked`).
  * **Single Image Mode:** Focus on a single photo with full preview. Destination folder selection is deferred until you click **"Save / Export Image"**.
* **🎨 Modern UI Design:**
  * **Left Sidebar Navigation:** Quickly switch between Master Settings, RKM Logo, Club Logo, QR Code, Copyright, and Custom Text.
  * **Scrollable Control Panel:** Card-grouped controls that automatically adapt without getting cut off on lower-resolution screens.
  * **Live Readout Sliders:** Always-visible percentages and degree values right next to every scale slider.
* **🖱️ Spontaneous Preview Interactivity:**
  * Hovering over any element on the preview canvas auto-selects it.
  * Mouse-wheel scrolling anywhere on the preview canvas scales the element spontaneously in real-time.
* **🖼️ Multiple Watermark Overlays:**
  * **RKM Logo** (Color & B&W version toggle)
  * **Photography Club Logo**
  * **QR Code**
  * **Copyright Information** (with text rotation, custom font, and optional background box)
  * **Custom Text Watermark**
* **📐 Resolution-Independent Scaling:** Watermark dimensions and border padding adapt proportionally based on the longest edge of each photo, ensuring identical visual proportions across different camera resolutions.
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

# Run v3.5.0
python production.py
```

---

## 🏗️ Building Executables (PyInstaller)

To build a standalone `.exe` from source:

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller --noconfirm --onefile --windowed --name RKMVPC --icon logo.ico --add-data "rkm_logo.png;." --add-data "bnw_rkm_logo.png;." --add-data "logo.png;." production.py
```

The output executable will be generated at `dist/RKMVPC.exe`.

---

## 🏷️ Version Control & Release Best Practices

To maintain past versions and release future updates cleanly on GitHub:

1. **Tagging Releases via Git CLI:**
   ```bash
   # Create a version tag
   git tag -a v3.5.0 -m "Release v3.5.0 - Full UI redesign & spontaneous scroll scaling"
   
   # Push tag to GitHub
   git push origin v3.5.0
   ```

2. **Publishing a GitHub Release:**
   - Go to your GitHub repository -> **Releases** -> **Draft a new release**.
   - Select tag `v3.5.0`.
   - Upload `dist/RKMVPC.exe` directly under **Attach binaries by dropping them here**.
   - This provides official GitHub release badges and download metrics!

---

## 📄 License

This project is maintained by **Tech Society of Vidyamandira** for the **Photography Club**. Distributed under the [MIT License](LICENSE).
