# RKMVPC Watermark & Photo Utility

[![Download Latest Release](https://img.shields.io/badge/Download-RKMVPC.exe-brightgreen?style=for-the-badge&logo=windows)](https://github.com/ManaswiDutta/RKMVPC-Watermark/releases/latest/download/RKMVPC.exe)

> ⚡ **Quick Start:** Click the button above to download the latest executable version of the watermark tool for Windows.

# RKMVPC Watermark & Photo Utility

A lightweight, framework-free desktop application designed for the RKMVM Photography Club to streamline image watermarking, basic editing, and preparation for the automated gallery website.

## 🎯 Overview
Managing event photos requires consistent branding and proper formatting before they are uploaded to the club's cloud storage. This tool eliminates the need for heavy, commercial photo editors by providing a custom, single-purpose interface to batch-process images efficiently.

Built completely from scratch using standard Python libraries, ensuring zero dependency bloat and rapid execution.

## ✨ Features
*   **Batch Watermarking:** Apply the official RKMVPC logo to multiple images simultaneously.
*   **Positioning & Scaling:** dynamically calculate watermark placement (e.g., bottom-right) based on the aspect ratio of the source image.
*   **Lightweight GUI:** A clean, intuitive user interface built natively with `tkinter`.
*   **Format Conversion:** Standardize outputs to `.jpg` or `.png` to ensure compatibility with the club's web gallery scripts.
*   **Zero-Framework Architecture:** Core logic is written in raw Python, keeping the software highly maintainable and educational for club members.

## 🛠️ Prerequisites
Because this project avoids heavy external frameworks, the requirements are minimal:
*   Python 3.8 or higher.
*   `Pillow` (PIL) for raw image matrix manipulation.
*   `tkinter` (Usually bundled with standard Python installations).

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/rkmvpc-watermark.git](https://github.com/yourusername/rkmvpc-watermark.git)
