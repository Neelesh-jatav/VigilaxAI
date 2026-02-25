# Drone Detection System (Flask)

Production-ready Flask application for live multi-camera streaming with modular architecture using **Application Factory + Blueprint + Service Layer**.

## Features

- Detect cameras (`/api/cameras`)
- Select/switch camera at runtime (`/api/select_camera`)
- Start/stop camera stream
- Live MJPEG multipart streaming (`/video_feed`)
- Capture image snapshots
- Start/stop video recording
- Thread-safe camera handling with clean resource release
- Gunicorn-ready deployment
- Adaptive low-light enhancement for dark environments

## Project Structure

```text
camera_feed_app/
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   └── camera_routes.py
│   ├── services/
│   │   └── camera_service.py
│   ├── utils/
│   │   └── camera_utils.py
│   ├── static/
│   │   ├── css/style.css
│   │   ├── captures/
│   │   └── recordings/
│   └── templates/
│       └── index.html
├── config.py
├── run.py
├── requirements.txt
├── Procfile
├── README.md
└── .env
```

## API Endpoints

- `GET /api/cameras` - list available cameras
- `POST /api/select_camera` - switch selected camera (`{"index": 0}`)
- `POST /api/start` - start camera if not running
- `POST /api/stop` - stop camera and release resources
- `GET /video_feed` - live MJPEG stream
- `POST /api/capture` - save image to `app/static/captures/`
- `POST /api/record/start` - start recording to `app/static/recordings/`
- `POST /api/record/stop` - stop active recording
- `GET /api/status` - current camera state
- `GET /api/fps` - current FPS value for active stream

## Local Run

1. Create virtual env and install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run application:

   ```bash
   python run.py
   ```

3. Open browser:

   ```
   http://127.0.0.1:5000
   ```

## Production Run

```bash
gunicorn run:app
```

`Procfile` already binds to `0.0.0.0` and uses `${PORT}` fallback.

## Notes

- Camera names are represented as `Camera {index}` for cross-platform consistency.
- On systems with multiple devices, scan range is configurable via `CAMERA_SCAN_MAX_INDEX`.
- Always ensure another process is not locking the camera device.

## Low-Light Tuning

When scenes are very dark, the app auto-enhances frames before streaming.

- `LOW_LIGHT_ENHANCEMENT_ENABLED` (`true`/`false`) toggles enhancement.
- `LOW_LIGHT_LUMA_THRESHOLD` increases sensitivity to dark frames.
- `LOW_LIGHT_CLAHE_CLIP_LIMIT` increases local contrast enhancement.
- `LOW_LIGHT_GAMMA` brightens mid-tones.
- `LOW_LIGHT_MAX_GAIN` caps brightness amplification to avoid heavy noise.
