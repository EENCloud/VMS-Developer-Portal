# Eagle Eye Networks OAuth Demo — Setup Guide

A Python demo for the Eagle Eye Networks API v3. Authenticates via OAuth 2.0,
lists cameras, and streams live RTSP video using GStreamer.

**No pip dependencies** — the core OAuth/API code uses only the Python standard
library. The video streaming modules (`frames_gst.py`, `measure_latency.py`)
require GStreamer and OpenCV, detailed below.

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```
EEN_CLIENT_ID=your_client_id_here
EEN_CLIENT_SECRET=your_client_secret_here
EEN_CAMERA_ID=your_camera_id_here
```

Obtain credentials from the [Eagle Eye Networks Developer Portal](https://developer.eagleeyenetworks.com/).
The redirect URI `http://127.0.0.1:3333/callback` must be registered in your app settings.

---

## Usage

```bash
python main.py login    # Run the full OAuth authorization flow
python main.py cameras  # List cameras (requires prior login)
python main.py stream   # Print the RTSP URL for the configured camera
python main.py refresh  # Manually refresh the stored access token
```

---

## Setup — Windows

### Requirements
- Windows 10/11 (64-bit)
- Python 3.10 or newer: https://www.python.org/downloads/

### Steps

1. **Clone / copy the project files** into a folder, e.g. `C:\Users\you\een-demo`.

2. **Create `.env`** from `.env.example`:
   ```
   copy .env.example .env
   ```
   Open `.env` in Notepad and fill in your credentials.

3. **Verify Python version** (must be 3.10+):
   ```cmd
   python --version
   ```

4. **Run the login flow:**
   ```cmd
   python main.py login
   ```
   Your browser will open for authorization. After approving, tokens are saved to `tokens.json`.

5. **List cameras:**
   ```cmd
   python main.py cameras
   ```

### Video streaming on Windows (optional)

`frames_gst.py` and `measure_latency.py` require GStreamer and OpenCV.
The easiest path on Windows is to use WSL2 (see Linux section below),
since GStreamer is much simpler to install there.

If you want native Windows support:

1. Install [GStreamer 1.24+ runtime + development](https://gstreamer.freedesktop.org/download/#windows)
   — choose the **MSVC 64-bit** installer. Install **both** the Runtime and Development packages.

2. Add GStreamer to your PATH (the installer can do this automatically):
   ```
   C:\gstreamer\1.0\msvc_x86_64\bin
   ```

3. Install Python bindings and OpenCV:
   ```cmd
   pip install PyGObject opencv-python numpy
   ```

---

## Virtual Environment

The `.venv` directory is excluded from version control. Recreate it with:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Linux / WSL2
# .venv\Scripts\activate         # Windows (cmd/PowerShell)
pip install opencv-python-headless numpy
```

> On WSL2 with a display, use `opencv-python` instead of `opencv-python-headless`.

---

## Setup — Linux / WSL2

### Requirements
- Python 3.10+
- GStreamer 1.0 (for video streaming)

### Steps

1. **Clone / copy the project files.**

2. **Create `.env`** from `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your credentials.

3. **Verify Python version** (must be 3.10+):
   ```bash
   python3 --version
   ```

4. **Install GStreamer system packages** (required for `frames_gst.py`):
   ```bash
   sudo apt update
   sudo apt install -y \
       python3-gi python3-gi-cairo gir1.2-gst-plugins-base-1.0 \
       gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
       gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
       gstreamer1.0-rtsp gstreamer1.0-tools \
       libgstreamer1.0-dev
   ```

5. **Install OpenCV and NumPy** (required for frame display and saving):
   ```bash
   pip install opencv-python numpy
   ```
   > On WSL2 without a display, use `opencv-python-headless` instead:
   > ```bash
   > pip install opencv-python-headless numpy
   > ```

6. **Run the login flow:**
   ```bash
   python3 main.py login
   ```
   Your browser will open for authorization. After approving, tokens are saved to `tokens.json`.

7. **List cameras:**
   ```bash
   python3 main.py cameras
   ```

8. **Measure stream latency** (requires GStreamer + OpenCV):
   ```bash
   python3 measure_latency.py
   ```

### WSL2 notes

- The OAuth callback server listens on `127.0.0.1:3333`. If your browser is on Windows,
  the callback will reach WSL2 automatically via the WSL2 localhost proxy (Windows 11 / WSL2 0.67+).
  On older setups you may need to run the login step from a Windows terminal instead.
- Live display via `cv2.imshow` requires an X11 server (e.g. VcXsrv, X410) and
  `export DISPLAY=:0` set in your shell. For headless use, `opencv-python-headless` is sufficient.
