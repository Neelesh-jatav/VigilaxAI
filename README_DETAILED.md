# VigilaxAI — Detailed Technical README

![Stack](https://img.shields.io/badge/Stack-Python%20%2B%20Flask-3776ab?style=for-the-badge)
![Vision](https://img.shields.io/badge/Computer%20Vision-OpenCV%20%2B%20YOLO-5c3ee8?style=for-the-badge)
![Audio](https://img.shields.io/badge/Audio%20AI-TensorFlow%20%2B%20librosa-ff6f00?style=for-the-badge)
![Frontend](https://img.shields.io/badge/Frontend-HTML%20%2B%20CSS%20%2B%20JavaScript-0ea5e9?style=for-the-badge)
![Streaming](https://img.shields.io/badge/Streaming-MJPEG-informational?style=for-the-badge)
![Deploy](https://img.shields.io/badge/Deploy-Gunicorn%20%2B%20Procfile-22c55e?style=for-the-badge)

VigilaxAI is a production-oriented Flask surveillance platform for real-time monitoring with multi-camera control, live MJPEG streaming, visual threat detection (face/drone/weapon), and audio-based drone signature analysis.

---

## 1) Project Overview

### Problem Statement
Security monitoring often requires running multiple threat detectors (visual + audio) at once, but many systems split capabilities across separate tools with no unified operator interface.

### Solution
VigilaxAI consolidates:
- Camera control + stream operations
- Multiple AI toggles (face, drone, knife, gun)
- Audio drone inference (upload + live microphone pipeline from browser)
- Capture/record/archive workflows
- Optional voice-command control and map-based route utility

### Target Users
- Site/perimeter operators
- Security monitoring teams
- Prototyping/research teams testing multi-modal detection workflows

---

## 2) System Architecture

### High-Level Components
- **Flask App Factory** initializes config/logging/blueprint.
- **CameraManager** orchestrates camera IO, frame loop, and AI pipeline.
- **Detection Services** implement modular inference for face, drone, weapon, and audio.
- **Browser Dashboard** handles controls, polling status, and live audio capture/visualization.

### Architecture Diagram

```text
+--------------------------------------------------------------------------------+
|                                 Browser UI                                     |
| index.html + style.css + JS (controls, polling, voice commands, map, audio)   |
+----------------------------+----------------------------+----------------------+
                             | HTTP/JSON + MJPEG stream
                             v
+--------------------------------------------------------------------------------+
|                              Flask Application                                 |
| create_app() -> camera_routes blueprint                                        |
| Endpoints: /video_feed, /api/*, /archives                                     |
+----------------------------+----------------------------+----------------------+
                             | uses
                             v
+--------------------------------------------------------------------------------+
|                                CameraManager                                   |
| - Camera open/scan/switch/start/stop                                           |
| - Reader thread + FPS + overlays                                                |
| - Capture/record + fallback storage                                              |
| - AI pipeline toggles                                                            |
+------------------+------------------+------------------+----------------------+
                   |                  |                  |
                   v                  v                  v
        FaceDetectionService   DroneDetectionService   WeaponDetectionService
        (OpenCV Haar)          (Roboflow API or YOLO) (Knife YOLO + Gun custom/Roboflow)

                   +----------------------------------------------------------+
                   | AudioDroneDetectionService                               |
                   | (TensorFlow model + librosa/scipy preprocessing)         |
                   +----------------------------------------------------------+
```

### Request/Response Example (Camera Stream Start)
1. Frontend posts `POST /api/start`.
2. Backend checks/opens camera if none active.
3. `CameraManager` starts reader thread.
4. Frontend uses `GET /video_feed` to render MJPEG stream.
5. Frontend polls `GET /api/status`, `GET /api/fps`, `GET /api/ai_status`.

---

## 3) Core Runtime Design

### Application Startup
- Entry point: `camera_feed_app/run.py`
- Factory: `camera_feed_app/app/__init__.py`
- Config source: `camera_feed_app/config.py`

### Configuration Model
`Config` is environment-variable driven and includes:
- Flask host/port/debug
- Camera scan/frame/FPS settings
- Low-light enhancement controls
- Drone backend selection (Roboflow preferred, YOLO fallback)
- Audio model path/threshold/spectrogram params
- Weapon settings for knife/gun backends

### Logging
- Python logging with optional `RotatingFileHandler` (`camera_feed_app.log`) in non-debug mode.
- Service-level logs for model loading, camera state changes, and detection errors.

---

## 4) Detection Pipeline (Visual + Audio)

### Visual Pipeline (Per Frame)
In camera reader loop:
1. Read frame
2. Apply low-light enhancement if enabled
3. Conditionally run enabled detectors:
   - Face detector
   - Drone detector
   - Weapon detector
4. Overlay FPS/camera metadata
5. Publish frame for stream/recording

### Face Detection
- OpenCV Haar cascade (`haarcascade_frontalface_default.xml`)
- Detection interval skipping to reduce CPU
- Overlay: face boxes + ON/OFF + count

### Drone Detection
- **Primary**: Roboflow inference API (`ROBOFLOW_API_KEY`, `ROBOFLOW_MODEL_ID`)
- **Fallback**: local `ultralytics.YOLO`
- Temporal noise filtering keeps stable detections and reduces flicker
- Overlay: red boxes + confidence labels + status panel

### Weapon Detection
- Knife detection via COCO class `43` on base YOLO model
- Gun detection via either:
  - custom YOLO model (`WEAPON_GUN_MODEL`), or
  - Roboflow backend (`WEAPON_GUN_ROBOFLOW_*`)
- Independent knife/gun toggles with combined counts

### Audio Drone Detection
- Loads TensorFlow/Keras model from `AUDIO_DRONE_MODEL_PATH`
- Preprocessing:
  - WAV magic-byte path via `scipy.io.wavfile` when possible
  - fallback via `librosa.load`
  - normalize/pad/truncate to fixed length
  - mel spectrogram + dB conversion
- Output:
  - `detected`, `prediction`, `confidence`, `raw_score`
- Optional persistence of positive detections into captures + JSON history log

---

## 5) API Surface

### UI/Pages
- `GET /` — main surveillance dashboard
- `GET /archives` — captures/recordings archive page
- `GET /archives/media/<media_type>/<filename>` — media fetch
- `POST /archives/captures/delete/<filename>` — delete capture

### Camera & Stream
- `GET /api/cameras`
- `POST /api/select_camera`
- `POST /api/start`
- `POST /api/stop`
- `GET /video_feed`
- `GET /api/status`
- `GET /api/fps`

### AI Control
- `POST /api/toggle_face`
- `POST /api/toggle_drone`
- `POST /api/toggle_knife`
- `POST /api/toggle_gun`
- `POST /api/toggle_weapon` (legacy)
- `GET /api/weapon_status`
- `GET /api/ai_status`

### Audio Drone
- `GET /api/audio_drone/status`
- `POST /api/audio_drone/predict` (multipart file)
- `GET /api/audio_drone/detections`
- `DELETE /api/audio_drone/detections/<filename>`

### Demo Testing
- `GET /api/demo_images` — list demo gallery images
- `GET /demo_image/<filename>` — serve demo image file
- `GET /api/demo_audio` — return configured demo audio metadata
- `GET /demo_audio/<filename>` — serve demo audio file

---

## 6) Frontend Behavior and UX Flows

### Dashboard Controls
- Camera selection buttons generated from `/api/cameras`
- Start/stop stream, capture, record controls
- AI toggles for face/drone/knife/gun
- Real-time status indicators for detector states and counts
- Demo Testing panel with auto-loading image gallery, manual run-detection button, and demo-audio analysis shortcut

### Live Audio Monitoring (Browser)
- Uses `navigator.mediaDevices.getUserMedia({ audio: true })`
- Web Audio API (`AudioContext`, `AnalyserNode`, script processor)
- Spectrum visualization on `<canvas>`
- Periodic inference using `/api/audio_drone/predict`
- Detection indicator + rolling event log
- Auto-save option writes positive detections to archive

### Voice Command Control
- Uses `SpeechRecognition` / `webkitSpeechRecognition`
- Commands mapped to UI actions (start/stop/capture/record, camera select, AI toggles, map/route commands, audio analysis)

### Route Map Utility
- Leaflet map panel
- Geocoding via Nominatim
- Route path via OSRM public API
- Displays route polyline and distance

---

## 7) Data & Storage Model

### Generated Media
- Captures: `camera_feed_app/app/static/captures/`
- Recordings: `camera_feed_app/app/static/recordings/`

### Audio Detection Persistence
- Saved files: `drone_audio_YYYYMMDD_HHMMSS.wav`
- Metadata log: `camera_feed_app/app/static/captures/audio_detections.json`

### Fallback Storage
If primary write paths fail, fallback path is used:
- `%TEMP%/camera_feed_app/captures`
- `%TEMP%/camera_feed_app/recordings`

---

## 8) Dependency Inventory

### Root Requirements
`requirements.txt` includes:
- `-r camera_feed_app/requirements.txt`

### Camera App Requirements (`camera_feed_app/requirements.txt`)
- `Flask==3.0.3`
- `opencv-python-headless==4.10.0.84`
- `gunicorn==22.0.0`
- `python-dotenv==1.0.1`
- `ultralytics>=8.3.0`
- `tensorflow>=2.14.0`
- `librosa>=0.10.0`
- `scipy>=1.11.0`
- `numpy>=1.24.0`

### Audio Training/Tooling (`audio1/requirements.txt`)
- `flask`, `numpy`, `librosa`, `matplotlib`, `tensorflow`, `scikit-learn`, `Pillow`

> Note: Audio inference in the integrated app requires TensorFlow + audio libraries to be installed in the active environment.

---

## 9) Project Structure (Current Repo)

```text
VigilaxAI/
├── camera_feed_app/
│   ├── app/
│   │   ├── routes/
│   │   │   └── camera_routes.py
│   │   ├── services/
│   │   │   ├── camera_service.py
│   │   │   ├── drone_detection_service.py
│   │   │   ├── face_detection_service.py
│   │   │   ├── weapon_detection_service.py
│   │   │   └── audio_drone_detection_service.py
│   │   ├── templates/
│   │   │   ├── index.html
│   │   │   └── archives.html
│   │   └── static/
│   │       ├── css/style.css
│   │       ├── captures/
│   │       └── recordings/
│   ├── config.py
│   ├── run.py
│   ├── requirements.txt
│   ├── Procfile
│   └── test_*.py
├── audio1/
│   ├── process_data.py
│   ├── train_model.py
│   ├── backend/model/drone_audio_model.h5
│   └── dataset/
├── render.yaml
├── runtime.txt
├── requirements.txt
└── README.md
```

---

## 9.1) Dual-App Topology (Important)

This repository contains two related but distinct Flask apps:

1. **Primary integrated app** (recommended): `camera_feed_app/`
  - Unified camera + visual AI + audio AI dashboard
  - Main API surface under `/api/*`
  - Main deployment target via root `Procfile`

2. **Standalone audio app**: `audio1/backend/app.py`
  - Legacy/specialized audio demo endpoint (`/predict`)
  - Useful for isolated model debugging and experimentation

### Practical Guidance
- Use `camera_feed_app` for all production-style local runs and integration testing.
- Use `audio1/backend/app.py` only when you want to debug the audio model independently of camera/visual services.

---

## 9.2) Environment Variable Matrix

All values are loaded in `camera_feed_app/config.py` with defaults.

### Flask Runtime
- `FLASK_HOST` (default `0.0.0.0`)
- `FLASK_PORT` (default `5000`, falls back to `PORT`)
- `FLASK_DEBUG` (default `false`)
- `LOG_LEVEL` (default `INFO`)

### Camera Runtime
- `CAMERA_SCAN_MAX_INDEX` (default `1`)
- `CAMERA_FPS` (default `20`)
- `CAMERA_FRAME_WIDTH` (default `1280`)
- `CAMERA_FRAME_HEIGHT` (default `720`)

### Low-Light Enhancement
- `LOW_LIGHT_ENHANCEMENT_ENABLED` (default `true`)
- `LOW_LIGHT_LUMA_THRESHOLD` (default `70`)
- `LOW_LIGHT_CLAHE_CLIP_LIMIT` (default `2.8`)
- `LOW_LIGHT_GAMMA` (default `1.35`)
- `LOW_LIGHT_MAX_GAIN` (default `2.8`)

### Drone Detection
- `ROBOFLOW_API_KEY` (default empty)
- `ROBOFLOW_MODEL_ID` (default `drone-dataset-jiusn/1`)
- `ROBOFLOW_SIZE` (default `640`)
- `DRONE_MODEL` (default `yolov8s.pt`)
- `DRONE_CONFIDENCE` (default `0.45`)
- `DRONE_CLASS_IDS` (default `4`)
- `DRONE_FRAME_SKIP` (default `2`)
- `DRONE_IOU_THRESHOLD` (default `0.45`)
- `DRONE_IMAGE_ENHANCE` (default `true`)

### Weapon Detection
- `WEAPON_BASE_MODEL` (default `yolov8n.pt`)
- `WEAPON_GUN_MODEL` (default empty)
- `WEAPON_GUN_ROBOFLOW_API_KEY` (default empty)
- `WEAPON_GUN_ROBOFLOW_MODEL_ID` (default empty)
- `WEAPON_GUN_ROBOFLOW_SIZE` (default `640`)
- `WEAPON_CONFIDENCE` (default `0.50`)
- `WEAPON_FRAME_SKIP` (default `3`)
- `WEAPON_IOU_THRESHOLD` (default `0.45`)

### Audio Drone Detection
- `AUDIO_DRONE_MODEL_PATH` (default points to `audio1/backend/model/drone_audio_model.h5`)
- `AUDIO_DRONE_CONFIDENCE` (default `0.50`)
- `AUDIO_DRONE_TARGET_SR` (default `16000`)
- `AUDIO_DRONE_DURATION_SECONDS` (default `3`)
- `AUDIO_DRONE_N_MELS` (default `128`)

---

## 10) Setup and Run Guide

### Prerequisites
- Python 3.10+ (3.11 recommended)
- Webcam/camera access for video features
- Optional: microphone access for live audio detection UI
- Optional: Roboflow API key(s)

### Local Setup (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run (Recommended from repo root)
```bash
python -m camera_feed_app.run
```

### Alternate (from `camera_feed_app/` directory)
```bash
cd camera_feed_app
python run.py
```

### Access
- `http://localhost:5000`

---

## 11) Deployment

### Procfile Options in Repo
- Root Procfile: `web: gunicorn camera_feed_app.run:app --bind 0.0.0.0:$PORT --timeout 180`
- App Procfile: `web: gunicorn run:app --bind 0.0.0.0:${PORT:-5000} --timeout 180` (from `camera_feed_app/` context)

### Render Blueprint (Included)
- `render.yaml` included at repo root
- `runtime.txt` pins Python runtime
- Build: `pip install -r requirements.txt`
- Start: `gunicorn camera_feed_app.run:app --bind 0.0.0.0:$PORT --timeout 180`

### Direct Gunicorn
```bash
gunicorn camera_feed_app.run:app --bind 0.0.0.0:$PORT --timeout 180
```

---

## 12) Testing and Validation

The repository includes script-style integration checks, including:
- route/API sanity checks
- camera switching behavior
- live detection/UI checks
- audio storage verification

Examples:
```bash
python camera_feed_app/test_routes.py
python camera_feed_app/test_live_detection.py
python camera_feed_app/test_audio_storage.py
```

---

## 13) Engineering Tradeoffs

- **Single-process app manager** simplifies local operations but centralizes state in-memory.
- **Frame-skip inference** improves responsiveness at the cost of per-frame precision.
- **Roboflow-first drone/gun path** reduces local model management but adds network dependency.
- **Threaded OpenCV capture loop** provides practical throughput, but system camera/driver behavior may vary by OS/hardware.
- **Audio pipeline optionality** keeps app usable even when TensorFlow is unavailable.

---

## 14) Known Constraints and Operational Notes

- If TensorFlow is missing, audio detector reports unavailable (visual detectors still work).
- Gun detection requires either custom gun model or Roboflow gun configuration.
- Camera discovery/opening can fail if camera is in use by another app.
- Multi-model inference can reduce FPS; UI already exposes warning state (`multi_ai_active`).

---

## 15) Suggested Next Improvements

- Add authentication and role-based access for operational deployments.
- Add structured observability (metrics/tracing/log enrichment).
- Add request throttling and security hardening middleware.
- Move detection history to durable DB for multi-instance deployments.
- Add automated pytest suite with CI pipeline and deterministic fixtures.

---

## 16) Useful Commands

```bash
# Run app
python -m camera_feed_app.run

# Install optional audio tooling (training/inference extras)
pip install -r audio1/requirements.txt

# Key checks
python test_detection_api.py
python verify_audio_implementation.py
python camera_feed_app/test_live_detection.py
```

---

## 16.1) QA Deep-Dive Findings (Repo Audit)

During full-project inspection, the following gaps were identified that may affect reproducibility:

1. **Some test scripts are stale vs current API fields**
  - A few scripts reference `both_active`, while runtime payload uses `multi_ai_active`.
  - Legacy endpoints (`/api/toggle_detection`, `/api/detection_status`) are present for compatibility, but modern flows should prefer `/api/toggle_face`, `/api/toggle_drone`, and `/api/ai_status`.

2. **Hard-coded absolute paths in helper scripts**
  - Some scripts target `c:/Users/neele/Downloads/vigilaxAI/...` and may fail in this workspace (`projects 2` path).
  - Prefer workspace-relative paths to improve portability.

3. **Security wording in older docs can be optimistic**
  - The app currently does not implement auth/RBAC in Flask routes.
  - Treat it as a local/controlled-network operator dashboard unless additional security middleware is added.

### Recommended Cleanup Backlog
- Normalize all test scripts to current API contract (`multi_ai_active` and latest status keys).
- Replace absolute file paths in scripts with `Path(__file__)` relative resolution.
- Add one canonical integration test entrypoint and mark older scripts as legacy.

---

## 16.2) Minimal Health Checks

Use these as quick smoke tests after startup:

```bash
curl http://127.0.0.1:5000/api/status
curl http://127.0.0.1:5000/api/ai_status
curl http://127.0.0.1:5000/api/audio_drone/status
curl http://127.0.0.1:5000/api/cameras
```

Expected high-level behavior:
- HTTP `200` responses
- `is_running` toggles with `/api/start` and `/api/stop`
- `audio_drone_available` is `false` when TensorFlow/model is missing, without crashing visual pipeline

---

## 16.3) Interview Questions (Top 20)

Use these to prepare for project walkthroughs and system-design discussions.

1. Why did you choose a Flask app-factory pattern for this surveillance system, and what would break if everything were global state?
   - **Ideal answer:** The app-factory pattern isolates configuration, logging, and blueprint registration, making the app testable and environment-driven. Pure global state would tightly couple startup order, make tests flaky, and complicate multi-instance deployment.
2. How does `CameraManager` coordinate camera IO, detection toggles, recording, and streaming without race conditions?
   - **Ideal answer:** Shared state is guarded with an `RLock`, while a dedicated reader thread performs capture/inference/write operations. Public methods update state atomically, and frame access uses lock-protected copies.
3. Why is the stream served as MJPEG (`/video_feed`) instead of WebRTC, and what are the tradeoffs?
   - **Ideal answer:** MJPEG is simple to implement in Flask and works well for rapid prototyping. Tradeoff: higher bandwidth and latency vs WebRTC, which is better for low-latency production streaming but more complex.
4. How does frame-skipping (`DRONE_FRAME_SKIP`, `WEAPON_FRAME_SKIP`) impact detection quality vs FPS?
   - **Ideal answer:** Skipping frames reduces inference cost and increases throughput/FPS. The downside is lower temporal granularity, so short-lived objects may be missed between analyzed frames.
5. Explain the full visual pipeline from frame capture to overlays and archived output.
   - **Ideal answer:** Camera frame is read, optionally low-light enhanced, then passed through enabled detectors (face/drone/weapon), annotated with bounding boxes and metadata (FPS/camera), then served to MJPEG and optionally written to capture/record outputs.
6. How does low-light enhancement work, and when can it hurt detection quality?
   - **Ideal answer:** It estimates scene luminance, applies gain + CLAHE + gamma LUT when dark. It can hurt quality by amplifying noise or causing over-enhancement artifacts in borderline lighting.
7. Why is drone detection implemented with Roboflow-primary and local YOLO fallback?
   - **Ideal answer:** Roboflow gives strong pretrained performance with minimal local setup; local YOLO provides offline/air-gapped fallback and avoids API dependency.
8. How does temporal filtering in drone detection reduce false positives?
   - **Ideal answer:** Lower-confidence detections are retained only if spatially consistent with prior frames, while high-confidence detections pass immediately. This suppresses one-frame noise spikes.
9. How are knife and gun detections separated architecturally, and why are they independently toggleable?
   - **Ideal answer:** Knife uses COCO class on a base YOLO model; gun uses custom YOLO or Roboflow backend. Independent toggles allow workload control, model availability fallback, and operator flexibility.
10. How does the audio drone pipeline convert raw audio into model-ready features (resample, pad, mel, dB)?
  - **Ideal answer:** Audio is loaded (scipy for WAV, librosa fallback), converted/normalized, resampled to target SR, padded/truncated to fixed duration, converted to mel spectrogram, transformed to dB, then reshaped for model inference.
11. What happens when TensorFlow is missing at runtime, and how does the system degrade gracefully?
  - **Ideal answer:** Audio service marks itself unavailable during model load; visual pipeline keeps running normally. API returns structured unavailable/error responses instead of crashing the app.
12. How is audio detection history persisted, and what are the scaling limits of JSON-file storage?
  - **Ideal answer:** Positive detections are copied to captures folder and indexed in `audio_detections.json`. JSON/file storage is simple but not ideal for concurrency, retention policies, or high-volume querying.
13. What are the biggest threading/performance risks in the current reader-loop design?
  - **Ideal answer:** Single-process threaded loops can bottleneck under heavy inference, and blocking operations may reduce frame freshness. Long-running model calls should be isolated or moved to worker processes.
14. How would you redesign this for multi-camera simultaneous ingestion at production scale?
  - **Ideal answer:** Use per-camera worker processes/containers, queue-based frame pipelines, shared metadata store, and a stream gateway. Separate control-plane APIs from data-plane inference.
15. Which endpoints are most critical for health monitoring, and what metrics/SLOs would you add first?
  - **Ideal answer:** Monitor `/api/status`, `/api/ai_status`, `/api/audio_drone/status`, and stream readiness. Add p95 latency, error rate, dropped frames, per-detector inference time, and uptime SLOs.
16. What security gaps exist today (auth, rate limits, upload constraints), and what would you fix first?
  - **Ideal answer:** Missing auth/RBAC and rate limiting are highest risk. First fixes: authentication, role checks, upload size/type quotas, and request throttling.
17. How would you harden file-upload and media-serving paths against abuse or path traversal?
  - **Ideal answer:** Keep strict extension + MIME checks, sanitize names, enforce size limits, store outside web root where possible, and validate path resolution against allowed directories.
18. How would you test this project beyond script-based checks (unit, integration, contract, load)?
  - **Ideal answer:** Add pytest unit tests for services, integration tests for routes with fixtures/mocks, API contract snapshots, and load tests for stream + inference endpoints.
19. What deployment differences matter between local `python -m camera_feed_app.run` and Gunicorn/Procfile execution?
  - **Ideal answer:** Gunicorn changes process model and lifecycle, affects logging and worker behavior, and relies on env-driven port binding. Production should use WSGI server tuning and health probes.
20. If asked to productionize this in 2 weeks, what would your prioritized implementation plan be?
  - **Ideal answer:** Week 1: security + observability + config hardening. Week 2: test automation, performance tuning, storage improvements, deployment pipeline, and rollout checklist with rollback plan.

### Quick Interview Tip
- Structure answers as: **Current design → tradeoff → improvement path**. That format shows practical ownership and engineering judgment.

---

## 17) License

No repository-level license file was detected at the time of writing. Add a root `LICENSE` file if you plan open-source distribution.

---

## 18) Maintainer

Project owner in repository metadata: **Neelesh Jatav**.

---

## 19) Additional Requested Project Summary

### 1. Project Title
**VigilaxAI – Integrated Surveillance & Defense System**

### 2. Project Objective / Statement
Modern warfare has shifted toward low-cost but high-impact drone threats, while traditional surveillance systems rely on separate tools for video monitoring, threat detection, and audio analysis, making operations complex and inefficient.

VigilaxAI was developed as a unified AI-powered surveillance platform that acts as a smart partner for combat and security missions by detecting drones, weapons, and faces from video streams while identifying drone activity through audio analysis in real time.

### 3. Technologies Used

#### Programming Languages
- Python (backend services and AI processing)
- JavaScript (frontend logic)
- HTML, CSS (user interface)

#### Application Type
- Flask-based web platform for real-time surveillance and AI inference
- Browser dashboard for monitoring and control

#### System Architecture
- Modular service-based backend
- Browser-based monitoring dashboard
- HTTP REST APIs for control
- MJPEG video streaming for live camera feed

#### Core Technologies
- Python
- Flask
- OpenCV
- Ultralytics YOLO
- TensorFlow / Keras
- Librosa & SciPy (audio preprocessing)

#### Frameworks
- Flask — web application framework
- TensorFlow / Keras — deep learning framework
- Ultralytics YOLO — object detection framework

#### Supporting Technologies
- Gunicorn — production WSGI server
- python-dotenv — environment configuration
- Roboflow API — optional cloud inference backend
- Leaflet.js — map visualization

#### Browser APIs Used
- MediaDevices / getUserMedia (microphone access)
- Web Audio API (audio processing)
- SpeechRecognition API (voice commands)
- Fetch API (frontend–backend communication)
- Canvas API (audio visualization)

#### Third-Party Python Packages
- Flask
- opencv-python
- ultralytics
- tensorflow
- librosa
- scipy
- numpy
- scikit-learn
- matplotlib
- Pillow
- gunicorn
- python-dotenv
- requests
- soundfile
- moviepy
- werkzeug

#### Python Standard Modules Used
- os
- json
- logging
- threading
- queue
- tempfile
- pathlib
- datetime
- typing
- base64
- urllib
- shutil
- traceback
- io
- collections

#### Internal Project Modules
**Routes**
- camera_routes

**Services**
- camera_service
- drone_detection_service
- weapon_detection_service
- face_detection_service
- audio_drone_detection_service

**Utilities**
- camera_utils

**Audio Pipeline Modules**
- audio_utils
- train_model
- process_data
- generate_noise
- fix_audio_files

### 4. Tools / Platforms Used
- GitHub – Version control
- Roboflow – Object detection dataset and inference
- Postman – API testing
- Google Colab – Model training experiments
- Gunicorn – Production deployment server

### 5. System Architecture / Workflow
Camera / Microphone Input
↓
Flask Backend Server (routes + API orchestration)
↓
AI Detection Pipeline
(Face | Drone | Weapon | Audio Drone)
↓
Frame Processing & Overlay (boxes, labels, FPS, camera metadata)
↓
Storage Layer (captures, recordings, audio detections log)
↓
Frontend Dashboard (live stream + controls + status)

#### Actual runtime flow
- Video path: camera frames go into a threaded manager loop, then optional low-light enhancement, then enabled visual detectors, then overlay, then MJPEG stream to UI.
- Audio path: browser microphone/audio upload sends WAV (or other allowed formats) to backend, backend preprocesses (SciPy/librosa) and runs TensorFlow inference, then returns detection/confidence JSON.
- Detector composition: face (OpenCV Haar), drone (Roboflow API with local YOLO fallback), weapon (knife via YOLO base model + gun via custom YOLO or Roboflow), audio drone (TensorFlow/Keras).
- Control plane: frontend toggles detectors and camera state through REST endpoints; backend exposes combined AI status and per-module status.

#### Storage details (important)
- No relational/NoSQL database is used.
- Primary persistence is filesystem: image captures, video recordings, saved detected audio clips.
- Metadata log is JSON (audio detection history).
- Fallback temp storage is used when primary write paths fail.

The system processes video frames and audio signals in real time, runs AI detection models, and streams results through a web dashboard.

### 6. Key Features / Modules
- Real-time multi-camera video streaming
- Face detection using OpenCV Haar cascade
- Drone detection using Roboflow API or YOLO models
- Weapon detection (knife & gun)
- Audio-based drone detection using spectrogram analysis
- Capture and recording system
- Live operator dashboard
- Voice command control
- Map-based route utility
- Detection history and archive management

### 7. Components of the Project
- Input Layer: Camera video input and microphone/audio input (live and uploaded files).
- Backend Server: Flask app with routes for streaming, controls, AI toggles, capture/record, archives, and audio prediction APIs.
- Camera Management Core: Camera manager that handles device scan/switch, threaded frame reading, FPS tracking, and stream lifecycle.
- AI Detection Services:
  - Face Detection (OpenCV Haar cascade)
  - Drone Detection (Roboflow API or local YOLO fallback)
  - Weapon Detection (knife and gun paths)
  - Audio Drone Detection (TensorFlow/Keras model with audio preprocessing)
- Frame Processing Layer: Low-light enhancement, per-frame AI inference, bounding-box/status overlays, MJPEG frame encoding.
- Storage Layer: File-based captures, recordings, saved detected audio clips, and JSON detection history logs (with temp fallback storage).
- Frontend Dashboard: Live monitoring UI (HTML/CSS/JavaScript) for stream view, controls, statuses, archives, audio analysis, and alerts.
- Integration/Utilities: Config and environment-based settings, logging, helper utilities, and health/status endpoints.
- Testing/Verification Suite: API tests, camera switching tests, audio detection tests, and verification scripts.
- Deployment Layer: Gunicorn + Procfile runtime for production hosting.

### 8. Challenges & Solutions
**Challenge:**
Running multiple AI detectors simultaneously reduced system performance, affecting camera frame processing and database operations. Additionally, during development the entire local MongoDB cluster became invisible due to an incorrect MongoDB data directory (`dbPath`) configuration.

**Solution:**
Implemented frame skipping, modular AI detection toggles, and threaded camera processing to improve FPS and reduce processing load, and corrected the MongoDB data path/connection configuration, restoring all databases in the local cluster.

### 9. Results / Achievements
- Built a real-time surveillance system capable of multi-modal detection
- Achieved stable live monitoring with multiple AI detection modules
- Enabled integrated visual + audio threat detection in a single dashboard

### 10. Deployment / Testing
- Deployed on Render
- Application deployed using Gunicorn
- Tested using multiple API integration and detection test scripts
- Local deployment using Flask server and environment-based configuration

### 11. Project Link
- GitHub Repository: https://github.com/Neelesh-jatav/VigilaxAI
- Readme: GitHub
- Drive (backup): https://drive.google.com/drive/folders/1P2uKFh-Rrwgo-TZuGLUjUOQFq67JhgAL
- Live Project: https://vigilaxai.onrender.com