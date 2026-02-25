import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    PORT = int(os.getenv("FLASK_PORT", os.getenv("PORT", "5000")))
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    CAMERA_SCAN_MAX_INDEX = int(os.getenv("CAMERA_SCAN_MAX_INDEX", "1"))
    CAMERA_FPS = int(os.getenv("CAMERA_FPS", "20"))
    CAMERA_FRAME_WIDTH = int(os.getenv("CAMERA_FRAME_WIDTH", "1280"))
    CAMERA_FRAME_HEIGHT = int(os.getenv("CAMERA_FRAME_HEIGHT", "720"))
    LOW_LIGHT_ENHANCEMENT_ENABLED = os.getenv("LOW_LIGHT_ENHANCEMENT_ENABLED", "true").lower() == "true"
    LOW_LIGHT_LUMA_THRESHOLD = int(os.getenv("LOW_LIGHT_LUMA_THRESHOLD", "70"))
    LOW_LIGHT_CLAHE_CLIP_LIMIT = float(os.getenv("LOW_LIGHT_CLAHE_CLIP_LIMIT", "2.8"))
    LOW_LIGHT_GAMMA = float(os.getenv("LOW_LIGHT_GAMMA", "1.35"))
    LOW_LIGHT_MAX_GAIN = float(os.getenv("LOW_LIGHT_MAX_GAIN", "2.8"))

    CAPTURES_DIR = BASE_DIR / "app" / "static" / "captures"
    RECORDINGS_DIR = BASE_DIR / "app" / "static" / "recordings"

    # Drone Detection Configuration (face detection is handled separately)
    # Roboflow API settings (recommended) - uses serverless API, no local weights needed
    ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")  # Required for API-based detection
    ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID", "drone-dataset-jiusn/1")  # Roboflow project/version
    ROBOFLOW_SIZE = int(os.getenv("ROBOFLOW_SIZE", "640"))  # Inference image size
    
    # Legacy local YOLO model settings (if Roboflow API not configured)
    DRONE_MODEL = os.getenv("DRONE_MODEL", "yolov8s.pt")
    DRONE_CONFIDENCE = float(os.getenv("DRONE_CONFIDENCE", "0.45"))
    DRONE_CLASS_IDS = os.getenv("DRONE_CLASS_IDS", "4")  # COCO airplane proxy unless using a custom drone model
    DRONE_FRAME_SKIP = int(os.getenv("DRONE_FRAME_SKIP", "2"))
    DRONE_IOU_THRESHOLD = float(os.getenv("DRONE_IOU_THRESHOLD", "0.45"))
    DRONE_IMAGE_ENHANCE = os.getenv("DRONE_IMAGE_ENHANCE", "true").lower() == "true"

    # Audio Drone Detection Configuration (integrated from audio1 project)
    AUDIO_DRONE_MODEL_PATH = os.getenv(
        "AUDIO_DRONE_MODEL_PATH",
        str(BASE_DIR.parent / "audio1" / "backend" / "model" / "drone_audio_model.h5"),
    )
    AUDIO_DRONE_CONFIDENCE = float(os.getenv("AUDIO_DRONE_CONFIDENCE", "0.50"))
    AUDIO_DRONE_TARGET_SR = int(os.getenv("AUDIO_DRONE_TARGET_SR", "16000"))
    AUDIO_DRONE_DURATION_SECONDS = int(os.getenv("AUDIO_DRONE_DURATION_SECONDS", "3"))
    AUDIO_DRONE_N_MELS = int(os.getenv("AUDIO_DRONE_N_MELS", "128"))

    # Weapon Detection Configuration (knife + gun)
    WEAPON_BASE_MODEL = os.getenv("WEAPON_BASE_MODEL", "yolov8n.pt")  # Base YOLO for knife (COCO class 43)
    WEAPON_GUN_MODEL = os.getenv("WEAPON_GUN_MODEL", "")  # Optional custom gun model path
    WEAPON_GUN_ROBOFLOW_API_KEY = os.getenv("WEAPON_GUN_ROBOFLOW_API_KEY", "")
    WEAPON_GUN_ROBOFLOW_MODEL_ID = os.getenv("WEAPON_GUN_ROBOFLOW_MODEL_ID", "")
    WEAPON_GUN_ROBOFLOW_SIZE = int(os.getenv("WEAPON_GUN_ROBOFLOW_SIZE", "640"))
    WEAPON_CONFIDENCE = float(os.getenv("WEAPON_CONFIDENCE", "0.50"))
    WEAPON_FRAME_SKIP = int(os.getenv("WEAPON_FRAME_SKIP", "3"))  # Higher skip = less CPU
    WEAPON_IOU_THRESHOLD = float(os.getenv("WEAPON_IOU_THRESHOLD", "0.45"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
