# 🎥 VigilaxAI Camera Feed App

Flask-based real-time surveillance dashboard for camera streaming, AI-based threat detection, and audio drone analysis.

---

## ✨ Highlights

- 📹 Live camera preview with runtime camera switching
- 🎯 Visual drone detection (YOLO / Roboflow)
- 🎙️ Audio drone detection from uploaded files
- 🔴 Live microphone-based drone sound monitoring
- 🧑 Face detection
- 🔪🔫 Knife and gun detection
- 📸 Image capture and 🎬 video recording
- 🗂️ Archive browsing and saved audio detection history
- 🌙 Low-light enhancement for dark scenes

---

## 🧱 Architecture

This app follows a modular Flask structure:

- **Application Factory** in `app/__init__.py`
- **Blueprint routes** in `app/routes/camera_routes.py`
- **Service layer** for camera + AI logic in `app/services/`
- **Frontend UI** in `app/templates/` and `app/static/`

```text
camera_feed_app/
├── app/
│   ├── routes/
│   │   └── camera_routes.py
│   ├── services/
│   │   ├── camera_service.py
│   │   ├── drone_detection_service.py
│   │   ├── audio_drone_detection_service.py
│   │   ├── face_detection_service.py
│   │   └── weapon_detection_service.py
│   ├── templates/
│   └── static/
├── config.py
├── run.py
├── requirements.txt
└── Procfile
```

---

## 🚀 Run Locally

From `camera_feed_app/`:

```bash
pip install -r requirements.txt
python run.py
```

Open:

```text
http://localhost:5000
```

---

## 🌐 API Reference

### Camera & Streaming
- `GET /api/cameras`
- `POST /api/select_camera`
- `POST /api/start`
- `POST /api/stop`
- `GET /video_feed`
- `GET /api/status`
- `GET /api/fps`

### Media Operations
- `POST /api/capture`
- `POST /api/record/start`
- `POST /api/record/stop`
- `GET /archives`

### AI Controls
- `POST /api/toggle_face`
- `POST /api/toggle_drone`
- `POST /api/toggle_knife`
- `POST /api/toggle_gun`
- `POST /api/toggle_weapon` (legacy compatibility)
- `GET /api/weapon_status`
- `GET /api/ai_status`

### Audio Drone Detection
- `GET /api/audio_drone/status`
- `POST /api/audio_drone/predict`
- `GET /api/audio_drone/detections`
- `DELETE /api/audio_drone/detections/<filename>`

---

## ⚙️ Configuration

Settings are defined in `config.py` and can be overridden through environment variables.

Key groups:
- `FLASK_*` — host, port, debug mode
- `CAMERA_*` — scan range, FPS, frame size
- `LOW_LIGHT_*` — dark scene enhancement tuning
- `DRONE_*` / `ROBOFLOW_*` — visual drone detection backends
- `AUDIO_DRONE_*` — audio model path, threshold, mel settings
- `WEAPON_*` — knife/gun detection behavior

---

## 🛠️ Production

Run with Gunicorn:

```bash
gunicorn run:app
```

`Procfile` is included for platform deployment and binds with `${PORT}` fallback.

---

## 📌 Notes

- If a camera is in use by another app, stream startup may fail.
- Audio formats beyond WAV may require additional system codecs (for example, ffmpeg).
- Roboflow-based detection requires valid API credentials in environment variables.
