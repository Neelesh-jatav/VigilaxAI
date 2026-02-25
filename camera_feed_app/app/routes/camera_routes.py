import tempfile
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, jsonify, redirect, render_template, request, send_file, url_for

from app.services.camera_service import frame_generator, init_camera_manager


camera_bp = Blueprint("camera", __name__)


@camera_bp.record_once
def on_load(state):
    init_camera_manager(state.app.config)


def _manager():
    return init_camera_manager(current_app.config)


@camera_bp.get("/")
def index():
    return render_template("index.html")


@camera_bp.get("/archives")
def archives():
    def list_media(primary_directory: Path, fallback_directory: Path, media_type: str):
        files_by_name = {}

        for directory in (primary_directory, fallback_directory):
            if not directory.exists() or not directory.is_dir():
                continue

            for file_path in directory.iterdir():
                if not file_path.is_file():
                    continue

                if file_path.name in files_by_name:
                    continue

                stat = file_path.stat()
                files_by_name[file_path.name] = {
                    "name": file_path.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "modified": stat.st_mtime,
                    "url": url_for("camera.archives_media", media_type=media_type, filename=file_path.name),
                    "is_image": file_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"},
                    "is_video": file_path.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv", ".mjpeg"},
                }

        items = list(files_by_name.values())
        items.sort(key=lambda item: item["modified"], reverse=True)
        return items


    captures_dir = Path(current_app.config.get("CAPTURES_DIR"))
    recordings_dir = Path(current_app.config.get("RECORDINGS_DIR"))

    fallback_base = Path(tempfile.gettempdir()) / "camera_feed_app"
    fallback_captures_dir = fallback_base / "captures"
    fallback_recordings_dir = fallback_base / "recordings"

    captures = list_media(captures_dir, fallback_captures_dir, "capture")
    recordings = list_media(recordings_dir, fallback_recordings_dir, "recording")

    return render_template("archives.html", captures=captures, recordings=recordings)


@camera_bp.get("/archives/media/<media_type>/<path:filename>")
def archives_media(media_type: str, filename: str):
    if media_type not in {"capture", "recording"}:
        abort(404)

    safe_name = Path(filename).name
    if safe_name != filename:
        abort(400)

    fallback_base = Path(tempfile.gettempdir()) / "camera_feed_app"

    if media_type == "capture":
        primary_dir = Path(current_app.config.get("CAPTURES_DIR"))
        fallback_dir = fallback_base / "captures"
    else:
        primary_dir = Path(current_app.config.get("RECORDINGS_DIR"))
        fallback_dir = fallback_base / "recordings"

    for directory in (primary_dir, fallback_dir):
        file_path = directory / safe_name
        if file_path.exists() and file_path.is_file():
            return send_file(file_path)

    abort(404)


@camera_bp.post("/archives/captures/delete/<path:filename>")
def delete_capture(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        abort(400)

    captures_dir = Path(current_app.config.get("CAPTURES_DIR"))
    fallback_dir = Path(tempfile.gettempdir()) / "camera_feed_app" / "captures"

    for directory in (captures_dir, fallback_dir):
        file_path = directory / safe_name
        if file_path.exists() and file_path.is_file():
            file_path.unlink(missing_ok=True)
            break
    else:
        abort(404)

    return redirect(url_for("camera.archives"))


@camera_bp.get("/api/cameras")
def get_cameras():
    cameras = _manager().get_available_cameras()
    return jsonify({"success": True, "cameras": cameras})


@camera_bp.post("/api/select_camera")
def select_camera():
    data = request.get_json(silent=True) or {}
    index = data.get("index")

    if index is None:
        return jsonify({"success": False, "message": "Missing camera index"}), 400

    try:
        index = int(index)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid camera index"}), 400

    ok, message = _manager().open_camera(index)
    status = 200 if ok else 400
    return jsonify({"success": ok, "message": message, "selected_camera": f"Camera {index}" if ok else None}), status


@camera_bp.post("/api/start")
def start_camera():
    state = _manager().get_state()
    if state["active_camera_index"] is None:
        cameras = _manager().get_available_cameras()
        if not cameras:
            return jsonify({"success": False, "message": "No camera available"}), 400
        _manager().open_camera(cameras[0]["index"])

    return jsonify({"success": True, "message": "Camera started", "state": _manager().get_state()})


@camera_bp.post("/api/stop")
def stop_camera():
    ok, message = _manager().stop_camera()
    return jsonify({"success": ok, "message": message, "state": _manager().get_state()})


@camera_bp.get("/video_feed")
def video_feed():
    return Response(
        frame_generator(_manager()),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@camera_bp.post("/api/capture")
def capture_image():
    ok, message, filename = _manager().capture_image()
    status = 200 if ok else 400
    return jsonify({"success": ok, "message": message, "filename": filename}), status


@camera_bp.post("/api/record/start")
def start_recording():
    ok, message, filename = _manager().start_recording()
    status = 200 if ok else 400
    return jsonify({"success": ok, "message": message, "filename": filename, "state": _manager().get_state()}), status


@camera_bp.post("/api/record/stop")
def stop_recording():
    ok, message = _manager().stop_recording()
    return jsonify({"success": ok, "message": message, "state": _manager().get_state()})


@camera_bp.get("/api/status")
def status():
    return jsonify({"success": True, "state": _manager().get_state()})


@camera_bp.get("/api/fps")
def get_fps():
    return jsonify({"fps": _manager().get_fps()})


@camera_bp.post("/api/toggle_face")
def toggle_face():
    """Toggle face detection on/off."""
    enabled = _manager().toggle_face_detection()
    status = _manager().get_face_detection_status()
    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "faces_detected": status["faces_detected"],
            "message": f"Face detection {'enabled' if enabled else 'disabled'}",
        }
    )


@camera_bp.post("/api/toggle_drone")
def toggle_drone():
    """Toggle drone detection on/off."""
    enabled = _manager().toggle_drone_detection()
    status = _manager().get_drone_detection_status()
    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "drones_detected": status["drones_detected"],
            "message": f"Drone detection {'enabled' if enabled else 'disabled'}",
        }
    )


@camera_bp.post("/api/toggle_knife")
def toggle_knife():
    """Toggle knife detection on/off."""
    enabled = _manager().toggle_knife_detection()
    status = _manager().get_weapon_detection_status()
    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "knife_enabled": status["knife_enabled"],
            "gun_enabled": status["gun_enabled"],
            "knives_detected": status["knives_detected"],
            "guns_detected": status["guns_detected"],
            "total_weapons": status["total_weapons"],
            "message": f"Knife detection {'enabled' if enabled else 'disabled'}",
        }
    )


@camera_bp.post("/api/toggle_gun")
def toggle_gun():
    """Toggle gun detection on/off."""
    enabled = _manager().toggle_gun_detection()
    status = _manager().get_weapon_detection_status()
    gun_available = status.get("gun_available", False)
    gun_backend = status.get("gun_backend", "none")
    message = f"Gun detection {'enabled' if enabled else 'disabled'}"
    if not gun_available:
        message = "Gun detection unavailable: configure WEAPON_GUN_MODEL or WEAPON_GUN_ROBOFLOW_* settings"

    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "knife_enabled": status["knife_enabled"],
            "gun_enabled": status["gun_enabled"],
            "gun_available": gun_available,
            "gun_backend": gun_backend,
            "knives_detected": status["knives_detected"],
            "guns_detected": status["guns_detected"],
            "total_weapons": status["total_weapons"],
            "message": message,
        }
    )


@camera_bp.post("/api/toggle_weapon")
def toggle_weapon():
    """Backward-compatible endpoint - toggles both knife and gun together."""
    enabled = _manager().toggle_weapon_detection()
    status = _manager().get_weapon_detection_status()
    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "knife_enabled": status["knife_enabled"],
            "gun_enabled": status["gun_enabled"],
            "weapon_enabled": status["weapon_enabled"],
            "knives_detected": status["knives_detected"],
            "guns_detected": status["guns_detected"],
            "total_weapons": status["total_weapons"],
            "message": f"Weapon detection {'enabled' if enabled else 'disabled'}",
        }
    )


@camera_bp.get("/api/weapon_status")
def weapon_status():
    """Get weapon detection status."""
    status = _manager().get_weapon_detection_status()
    return jsonify(status)


@camera_bp.get("/api/ai_status")
def ai_status():
    """Get combined AI detection status for all models."""
    status = _manager().get_ai_status()
    return jsonify(status)


@camera_bp.get("/api/audio_drone/status")
def audio_drone_status():
    """Get audio drone detector availability and last inference result."""
    status = _manager().get_audio_drone_status()
    return jsonify({"success": True, **status})


@camera_bp.post("/api/audio_drone/predict")
def audio_drone_predict():
    """Predict drone presence from uploaded audio file."""
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"success": False, "message": "No audio file uploaded"}), 400

    allowed_exts = {"wav", "mp3", "ogg", "m4a", "flac"}
    extension = Path(file.filename).suffix.lower().lstrip(".")
    if extension not in allowed_exts:
        return jsonify({"success": False, "message": "Unsupported audio format"}), 400

    # Check if we should save detections
    save_detection = request.form.get("save_detection", "false").lower() == "true"
    source = request.form.get("source", "upload")

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as temp_file:
            temp_path = Path(temp_file.name)
            file.save(temp_file)

        result = _manager().analyze_audio_file(str(temp_path))
        
        # Save detection if requested and drone was detected
        if save_detection and result.get("detected") and result.get("success"):
            save_result = _manager().save_audio_detection(str(temp_path), result, source)
            result["saved"] = save_result.get("success", False)
            if save_result.get("success"):
                result["saved_filename"] = save_result.get("filename")
        
        status_code = 200 if result.get("success") else 503
        return jsonify(result), status_code
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


@camera_bp.route("/api/audio_drone/detections", methods=["GET"])
def audio_drone_detections():
    """Get detection history."""
    limit = request.args.get("limit", 50, type=int)
    detections = _manager().get_audio_detection_history(limit)
    return jsonify({"success": True, "detections": detections})


@camera_bp.route("/api/audio_drone/detections/<filename>", methods=["DELETE"])
def audio_drone_delete_detection(filename):
    """Delete a saved detection."""
    result = _manager().delete_audio_detection(filename)
    status_code = 200 if result.get("success") else 500
    return jsonify(result), status_code


# Legacy endpoints for backward compatibility
@camera_bp.post("/api/toggle_detection")
def toggle_detection():
    """Legacy endpoint - toggles face detection."""
    enabled = _manager().toggle_face_detection()
    status = _manager().get_face_detection_status()
    return jsonify(
        {
            "success": True,
            "enabled": enabled,
            "faces_detected": status["faces_detected"],
            "message": f"Detection {'enabled' if enabled else 'disabled'}",
        }
    )


@camera_bp.get("/api/detection_status")
def detection_status():
    """Legacy endpoint - returns face detection status."""
    status = _manager().get_face_detection_status()
    return jsonify(status)
