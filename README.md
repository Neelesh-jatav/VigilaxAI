# 🚁 VigilaxAI

AI-powered **Drone Detection & Surveillance System** with live video monitoring, multi-camera control, visual threat detection, and audio-based drone sound analysis.

---

## ✨ Overview

VigilaxAI combines computer vision + audio intelligence in a Flask-based web dashboard designed for real-time situational awareness.

It supports:
- 📹 Live camera streaming (single/multi-camera environments)
- 🎯 Visual drone detection
- 🎙️ Audio drone signature detection (TensorFlow model)
- 🧪 Demo Testing panel (auto-load demo images + one-click detection)
- 🎵 Demo MP3 analysis for drone-audio prediction
- 🧑 Face detection
- 🔪🔫 Weapon detection (knife/gun)
- 💾 Snapshot capture and video recording
- 🗂️ Archive browsing for saved media and audio detections

---

## 🧱 Project Structure

```text
VigilaxAI/
├── camera_feed_app/           # Main Flask surveillance app
│   ├── app/
│   │   ├── routes/            # API + page routes
│   │   ├── services/          # Camera + AI detection services
│   │   ├── templates/         # HTML UI
│   │   └── static/            # CSS, captures, recordings
│   ├── config.py              # Runtime/environment config
│   └── run.py                 # App entrypoint
├── audio1/                    # Audio model training + backend assets
└── requirements.txt           # Root dependency entrypoint
```

---

## 🚀 Quick Start

### 1) Clone the repository

```bash
git clone https://github.com/Neelesh-jatav/VigilaxAI.git
cd VigilaxAI
```

### 2) Create & activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

For full audio-model tooling/training extras:

```bash
pip install -r audio1/requirements.txt
```

### 4) Run the app

```bash
python camera_feed_app/run.py
```

Open in browser:

```text
http://localhost:5000
```
http://127.0.0.1:5000
---

## 🧪 Main API Endpoints

### Camera & Stream
- `GET /api/cameras` — list available cameras
- `POST /api/select_camera` — switch active camera
- `POST /api/start` / `POST /api/stop` — start/stop stream
- `GET /video_feed` — MJPEG live stream
- `GET /api/status` — current camera/service state

### Detection Controls
- `POST /api/toggle_face`
- `POST /api/toggle_drone`
- `POST /api/toggle_knife`
- `POST /api/toggle_gun`
- `GET /api/ai_status`

### Audio Drone Detection
- `GET /api/audio_drone/status`
- `POST /api/audio_drone/predict` (multipart file upload)
- `GET /api/audio_drone/detections`
- `DELETE /api/audio_drone/detections/<filename>`

### Demo Testing
- `GET /api/demo_images` — list demo images for gallery
- `GET /demo_image/<filename>` — serve demo image files
- `GET /api/demo_audio` — fetch configured demo audio metadata
- `GET /demo_audio/<filename>` — serve demo audio file

### Media & Archives
- `POST /api/capture`
- `POST /api/record/start`
- `POST /api/record/stop`
- `GET /archives`

---

## ⚙️ Configuration

Core settings are managed in `camera_feed_app/config.py` using environment variables.

Common options:
- `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG`
- `CAMERA_SCAN_MAX_INDEX`, `CAMERA_FPS`, frame size settings
- `DRONE_*` and `ROBOFLOW_*` for visual drone detection
- `AUDIO_DRONE_*` for audio model path, threshold, and spectrogram settings
- `WEAPON_*` for knife/gun detection behavior
- `DEMO_TESTING_DIR` for optional custom demo-media folder path

---

## ☁️ Render Deployment (Ready)

This repo is now configured for Render deployment.

Included deployment files:
- `render.yaml` (service blueprint)
- `runtime.txt` (Python runtime pin)
- `Procfile` (Gunicorn start command)

### Render Build/Start

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn camera_feed_app.run:app --bind 0.0.0.0:$PORT --timeout 180`

### Deploy Steps

1. Push code to GitHub.
2. In Render, create a **Web Service** from this repository.
3. Use the detected `render.yaml` blueprint, or manually set the same build/start commands.
4. Add required environment variables (if using Roboflow/custom models).
5. Deploy.

### Recommended Environment Variables

- `FLASK_DEBUG=false`
- `LOG_LEVEL=INFO`
- `ROBOFLOW_API_KEY` (optional, if using API-based drone model)
- `WEAPON_GUN_ROBOFLOW_API_KEY` (optional)
- `DEMO_TESTING_DIR` (optional; local Windows demo path will not exist on Render by default)

### Notes For Cloud Runtime

- OpenCV is configured via `opencv-python-headless` for Linux/cloud compatibility.
- Gunicorn timeout is set to `180` seconds to allow large AI models to load on startup.
- If demo media files are not available in cloud, demo endpoints return safe empty responses instead of failing app startup.

---

## 🧠 Tech Stack

- **Backend:** Flask, Python
- **Computer Vision:** OpenCV, Ultralytics YOLO, Roboflow API (optional)
- **Audio AI:** TensorFlow/Keras, librosa, NumPy
- **Frontend:** HTML, CSS, JavaScript
- **Deployment:** Gunicorn, Procfile-based hosting

---

## ✅ Useful Commands

Run selected tests/examples from repository root:

```bash
python test_detection_api.py
python verify_audio_implementation.py
python camera_feed_app/test_live_detection.py
```

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome.

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Open a pull request

---

## 📌 Notes

- Some advanced detection features require model files and/or external API keys.
- For audio upload support beyond WAV in some systems, installing `ffmpeg` can improve compatibility.

---

## 📄 License

Add your preferred license in this repository (for example: MIT) if not already set.

---

### Built for smarter perimeter awareness 👁️‍🗨️
