import logging
import queue
import threading
import tempfile
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.services.face_detection_service import FaceDetectionService
from app.services.drone_detection_service import DroneDetectionService
from app.services.audio_drone_detection_service import AudioDroneDetectionService
from app.services.weapon_detection_service import WeaponDetectionService


logger = logging.getLogger(__name__)


class CameraManager:
    def __init__(self, app_config) -> None:
        self._lock = threading.RLock()
        self._capture: Optional[cv2.VideoCapture] = None
        self._writer: Optional[cv2.VideoWriter] = None
        self._record_file_handle = None
        self._record_mode: Optional[str] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._active_camera_index: Optional[int] = None
        self._active_camera_name: Optional[str] = None

        self._is_running = False
        self._is_recording = False
        self._last_frame = None
        self._previous_frame_time: Optional[float] = None
        self._fps_samples = deque(maxlen=20)
        self._current_fps: float = 0.0

        self._scan_max_index = int(app_config["CAMERA_SCAN_MAX_INDEX"])
        self._fps = int(app_config["CAMERA_FPS"])
        self._frame_width = int(app_config["CAMERA_FRAME_WIDTH"])
        self._frame_height = int(app_config["CAMERA_FRAME_HEIGHT"])

        self._captures_dir = Path(app_config["CAPTURES_DIR"])
        self._recordings_dir = Path(app_config["RECORDINGS_DIR"])
        self._fallback_base_dir = Path(tempfile.gettempdir()) / "camera_feed_app"
        self._fallback_captures_dir = self._fallback_base_dir / "captures"
        self._fallback_recordings_dir = self._fallback_base_dir / "recordings"
        self._fallback_captures_dir.mkdir(parents=True, exist_ok=True)
        self._fallback_recordings_dir.mkdir(parents=True, exist_ok=True)

        self.face_detector = FaceDetectionService(
            cascade_path=app_config.get("FACE_CASCADE_PATH"),
            scale_factor=float(app_config.get("FACE_SCALE_FACTOR", 1.1)),
            min_neighbors=int(app_config.get("FACE_MIN_NEIGHBORS", 5)),
            min_size=(
                int(app_config.get("FACE_MIN_SIZE_W", 30)),
                int(app_config.get("FACE_MIN_SIZE_H", 30)),
            ),
            detection_interval=int(app_config.get("FACE_DETECTION_INTERVAL", 2)),
        )
        self.face_detector.load_model()
        self.face_enabled = False

        raw_drone_class_ids = str(app_config.get("DRONE_CLASS_IDS", "4"))
        drone_class_ids = [
            int(item.strip())
            for item in raw_drone_class_ids.split(",")
            if item.strip().isdigit()
        ]
        if not drone_class_ids:
            drone_class_ids = [4]

        self.drone_detector = DroneDetectionService(
            model_path=app_config.get("DRONE_MODEL", "yolov8s.pt"),
            confidence_threshold=float(app_config.get("DRONE_CONFIDENCE", 0.45)),
            drone_class_ids=drone_class_ids,
            detection_interval=int(app_config.get("DRONE_FRAME_SKIP", 2)),
            iou_threshold=float(app_config.get("DRONE_IOU_THRESHOLD", 0.45)),
            enable_preprocessing=bool(app_config.get("DRONE_IMAGE_ENHANCE", True)),
            roboflow_api_key=app_config.get("ROBOFLOW_API_KEY", ""),
            roboflow_model_id=app_config.get("ROBOFLOW_MODEL_ID", "drone-dataset-jiusn/1"),
            roboflow_size=int(app_config.get("ROBOFLOW_SIZE", 640)),
        )
        self.drone_detector.load_model()
        self.drone_enabled = False

        self.audio_drone_detector = AudioDroneDetectionService(
            model_path=app_config.get("AUDIO_DRONE_MODEL_PATH", ""),
            confidence_threshold=float(app_config.get("AUDIO_DRONE_CONFIDENCE", 0.5)),
            target_sr=int(app_config.get("AUDIO_DRONE_TARGET_SR", 16000)),
            duration_seconds=int(app_config.get("AUDIO_DRONE_DURATION_SECONDS", 3)),
            n_mels=int(app_config.get("AUDIO_DRONE_N_MELS", 128)),
        )
        self.audio_drone_detector.load_model()

        self.weapon_detector = WeaponDetectionService(
            base_model_path=app_config.get("WEAPON_BASE_MODEL", "yolov8n.pt"),
            gun_model_path=app_config.get("WEAPON_GUN_MODEL", ""),
            confidence_threshold=float(app_config.get("WEAPON_CONFIDENCE", 0.50)),
            detection_interval=int(app_config.get("WEAPON_FRAME_SKIP", 3)),
            iou_threshold=float(app_config.get("WEAPON_IOU_THRESHOLD", 0.45)),
            gun_roboflow_api_key=app_config.get("WEAPON_GUN_ROBOFLOW_API_KEY", ""),
            gun_roboflow_model_id=app_config.get("WEAPON_GUN_ROBOFLOW_MODEL_ID", ""),
            gun_roboflow_size=int(app_config.get("WEAPON_GUN_ROBOFLOW_SIZE", 640)),
        )
        self.weapon_detector.load_model()
        self.knife_enabled = False
        self.gun_enabled = False

        self._low_light_enabled = bool(app_config["LOW_LIGHT_ENHANCEMENT_ENABLED"])
        self._low_light_luma_threshold = int(app_config["LOW_LIGHT_LUMA_THRESHOLD"])
        self._low_light_clahe_clip_limit = float(app_config["LOW_LIGHT_CLAHE_CLIP_LIMIT"])
        self._low_light_gamma = float(app_config["LOW_LIGHT_GAMMA"])
        self._low_light_max_gain = float(app_config["LOW_LIGHT_MAX_GAIN"])

        self._clahe = cv2.createCLAHE(
            clipLimit=self._low_light_clahe_clip_limit,
            tileGridSize=(8, 8),
        )
        self._gamma_lut = self._build_gamma_lut(self._low_light_gamma)

    def _build_gamma_lut(self, gamma_value: float):
        gamma_value = max(gamma_value, 0.1)
        inv_gamma = 1.0 / gamma_value
        lut = np.array(
            [
                ((idx / 255.0) ** inv_gamma) * 255.0
                for idx in range(256)
            ],
            dtype=np.float32,
        )
        return np.clip(lut, 0, 255).astype(np.uint8)

    def _enhance_low_light(self, frame):
        if not self._low_light_enabled:
            return frame

        small = cv2.resize(frame, (160, 90), interpolation=cv2.INTER_AREA)
        gray_small = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        avg_luma = float(gray_small.mean())

        if avg_luma >= self._low_light_luma_threshold:
            return frame

        gain = min(self._low_light_max_gain, self._low_light_luma_threshold / max(avg_luma, 1.0))
        frame_gain = cv2.convertScaleAbs(frame, alpha=gain, beta=0)

        lab = cv2.cvtColor(frame_gain, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        l_enhanced = self._clahe.apply(l_channel)
        enhanced_lab = cv2.merge((l_enhanced, a_channel, b_channel))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        return cv2.LUT(enhanced_bgr, self._gamma_lut)

    def _reset_fps(self) -> None:
        self._previous_frame_time = None
        self._fps_samples.clear()
        self._current_fps = 0.0

    def _update_fps(self) -> float:
        now = time.time()
        if self._previous_frame_time is None:
            self._previous_frame_time = now
            return self._current_fps

        elapsed = now - self._previous_frame_time
        self._previous_frame_time = now
        if elapsed <= 0:
            return self._current_fps

        instant_fps = 1.0 / elapsed
        self._fps_samples.append(instant_fps)
        if self._fps_samples:
            self._current_fps = sum(self._fps_samples) / len(self._fps_samples)

        return self._current_fps

    def _overlay_frame_metadata(self, frame, fps_value: float):
        camera_name = self._active_camera_name or "None"
        frame_h = frame.shape[0]
        cv2.putText(
            frame,
            f"FPS: {fps_value:.2f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Camera: {camera_name}",
            (10, max(25, frame_h - 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return frame

    def _reader_loop(self) -> None:
        while True:
            with self._lock:
                if not self._is_running or self._capture is None or not self._capture.isOpened():
                    break
                capture = self._capture
                recording = self._is_recording
                writer = self._writer

            ok, frame = capture.read()
            if not ok:
                time.sleep(0.03)
                continue

            frame = self._enhance_low_light(frame)
            
            # AI Detection Pipeline - Independent toggles for performance control
            if self.face_enabled:
                frame = self.face_detector.detect_faces(frame)
            if self.drone_enabled:
                frame = self.drone_detector.detect_drones(frame)
            if self.knife_enabled or self.gun_enabled:
                frame = self.weapon_detector.detect_weapons(frame)

            with self._lock:
                fps_value = self._update_fps()
                frame = self._overlay_frame_metadata(frame, fps_value)
                self._last_frame = frame
                if recording and writer is not None:
                    writer.write(frame)
                elif recording and self._record_mode == "mjpeg" and self._record_file_handle is not None:
                    ok_enc, encoded = cv2.imencode(".jpg", frame)
                    if ok_enc:
                        self._record_file_handle.write(encoded.tobytes())
                        self._record_file_handle.write(b"\n--frame--\n")

            time.sleep(max(1 / max(self._fps, 1), 0.01))

    def get_available_cameras(self) -> List[Dict[str, object]]:
        """Fast camera detection with timeout protection."""
        available = []
        for index in range(0, self._scan_max_index + 1):
            try:
                # Use a thread with timeout to prevent hanging
                result_queue = queue.Queue()
                
                def probe_camera():
                    try:
                        temp_capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # Direct Show for Windows (faster)
                        if temp_capture is None or not temp_capture.isOpened():
                            if temp_capture is not None:
                                temp_capture.release()
                            result_queue.put((False, None))
                            return
                        
                        # Skip frame read during scan - just check if it opens
                        temp_capture.release()
                        result_queue.put((True, index))
                    except Exception:
                        result_queue.put((False, None))
                
                probe_thread = threading.Thread(target=probe_camera, daemon=True)
                probe_thread.start()
                probe_thread.join(timeout=1.0)  # 1 second timeout per camera
                
                try:
                    success, cam_index = result_queue.get_nowait()
                    if success and cam_index is not None:
                        available.append({"index": cam_index, "name": f"Camera {cam_index}"})
                except queue.Empty:
                    logger.debug(f"Camera {index} probe timed out")
                    
            except Exception as e:
                logger.debug(f"Camera {index} probe error: {e}")
                continue
        
        logger.info(f"Camera scan complete: found {len(available)} camera(s)")
        return available

    def open_camera(self, index: int) -> Tuple[bool, str]:
        with self._lock:
            if self._active_camera_index == index and self._capture is not None and self._capture.isOpened():
                return True, f"Camera {index} already active"

            # Always release current camera before opening a new one
            if self._capture is not None:
                logger.info(f"Switching from camera {self._active_camera_index} to {index}")
            self.release_camera()

            # Open camera with timeout validation
            result_queue = queue.Queue()
            
            def open_and_validate():
                try:
                    temp_cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                    if temp_cap is None or not temp_cap.isOpened():
                        if temp_cap:
                            temp_cap.release()
                        result_queue.put((False, "Camera failed to open"))
                        return
                    
                    # Configure camera
                    temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._frame_width)
                    temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._frame_height)
                    temp_cap.set(cv2.CAP_PROP_FPS, self._fps)
                    temp_cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75)
                    temp_cap.set(cv2.CAP_PROP_AUTO_WB, 1)
                    temp_cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
                    
                    # Validate can read frames
                    success, frame = temp_cap.read()
                    if not success or frame is None:
                        temp_cap.release()
                        result_queue.put((False, "Camera cannot read frames"))
                        return
                    
                    result_queue.put((True, temp_cap))
                except Exception as e:
                    result_queue.put((False, str(e)))
            
            open_thread = threading.Thread(target=open_and_validate, daemon=True)
            open_thread.start()
            open_thread.join(timeout=3.0)  # 3 second timeout to open and validate
            
            try:
                success, result = result_queue.get_nowait()
                if not success:
                    logger.warning(f"Camera {index} validation failed: {result}")
                    return False, f"Camera {index} not available: {result}"
                capture = result
            except queue.Empty:
                logger.warning(f"Camera {index} open timed out")
                return False, f"Camera {index} timed out"

            self._capture = capture
            self._active_camera_index = index
            self._active_camera_name = f"Camera {index}"
            self._is_running = True
            self._is_recording = False
            self._last_frame = None
            self._reset_fps()

            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()
            logger.info("Camera opened index=%s", index)
            return True, f"Camera {index} selected"

    def release_camera(self) -> None:
        with self._lock:
            if self._writer is not None:
                self._writer.release()
                self._writer = None
            if self._record_file_handle is not None:
                self._record_file_handle.close()
                self._record_file_handle = None
            self._record_mode = None

            if self._capture is not None:
                self._capture.release()
                self._capture = None

            self._is_recording = False
            self._is_running = False
            self._last_frame = None
            self._active_camera_index = None
            self._active_camera_name = None
            self._reader_thread = None
            # Reset detection states
            if self.face_enabled:
                self.face_enabled = self.face_detector.toggle_detection()
            if self.drone_enabled:
                self.drone_enabled = self.drone_detector.toggle_detection()
            if self.knife_enabled:
                self.knife_enabled = self.weapon_detector.toggle_knife_detection()
            if self.gun_enabled:
                self.gun_enabled = self.weapon_detector.toggle_gun_detection()
            self._reset_fps()
            logger.info("Camera resources released")

    def get_frame(self):
        with self._lock:
            if self._capture is None or not self._capture.isOpened() or not self._is_running:
                return None
            if self._last_frame is not None:
                return self._last_frame.copy()

        with self._lock:
            if self._capture is None or not self._capture.isOpened() or not self._is_running:
                return None
            ok, frame = self._capture.read()
            if not ok:
                return None
            frame = self._enhance_low_light(frame)
            
            # AI Detection Pipeline - fallback path
            if self.face_enabled:
                frame = self.face_detector.detect_faces(frame)
            if self.drone_enabled:
                frame = self.drone_detector.detect_drones(frame)
            if self.knife_enabled or self.gun_enabled:
                frame = self.weapon_detector.detect_weapons(frame)
            
            fps_value = self._update_fps()
            frame = self._overlay_frame_metadata(frame, fps_value)
            self._last_frame = frame
            if self._is_recording and self._writer is not None:
                self._writer.write(frame)
            return frame.copy()

    def get_encoded_frame(self) -> Optional[bytes]:
        frame = self.get_frame()
        if frame is None:
            return None

        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            return None

        return encoded.tobytes()

    def capture_image(self) -> Tuple[bool, str, Optional[str]]:
        with self._lock:
            frame = self._last_frame
            if frame is None:
                frame = self.get_frame()

            if frame is None:
                return False, "No frame available to capture", None

            filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                return False, "Failed to encode image", None

            self._captures_dir.mkdir(parents=True, exist_ok=True)
            path = self._captures_dir / filename
            try:
                path.write_bytes(encoded.tobytes())
            except OSError:
                fallback_path = self._fallback_captures_dir / filename
                try:
                    fallback_path.write_bytes(encoded.tobytes())
                    logger.warning("Primary capture path failed, saved to fallback: %s", fallback_path)
                    return True, "Image captured (fallback path)", filename
                except OSError:
                    return False, "Failed to save image", None

            logger.info("Image captured: %s", path)
            return True, "Image captured", filename

    def start_recording(self) -> Tuple[bool, str, Optional[str]]:
        with self._lock:
            if self._is_recording:
                return True, "Recording already in progress", None

            if self._capture is None or not self._capture.isOpened() or not self._is_running:
                return False, "Start camera before recording", None

            width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or self._frame_width
            height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or self._frame_height

            self._recordings_dir.mkdir(parents=True, exist_ok=True)
            base_name = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            writer = None
            filename = None
            selected_recording_path = None

            codec_candidates = [
                ("XVID", ".avi"),
                ("MJPG", ".avi"),
                ("mp4v", ".mp4"),
            ]

            for codec, extension in codec_candidates:
                candidate_filename = f"{base_name}{extension}"
                candidate_path = self._recordings_dir / candidate_filename
                fourcc = cv2.VideoWriter_fourcc(*codec)
                candidate_writer = cv2.VideoWriter(
                    str(candidate_path),
                    fourcc,
                    float(max(self._fps, 1)),
                    (width, height),
                )
                if candidate_writer.isOpened():
                    writer = candidate_writer
                    filename = candidate_filename
                    self._record_mode = "video"
                    selected_recording_path = candidate_path
                    break
                candidate_writer.release()

            if writer is None or filename is None:
                fallback_filename = f"{base_name}.mjpeg"
                fallback_path = self._fallback_recordings_dir / fallback_filename
                try:
                    self._record_file_handle = open(fallback_path, "wb")
                    self._record_mode = "mjpeg"
                    self._writer = None
                    self._is_recording = True
                    logger.warning("OpenCV codecs unavailable, recording MJPEG fallback: %s", fallback_path)
                    return True, "Recording started (mjpeg fallback)", fallback_filename
                except OSError:
                    return False, "Failed to start recording", None

            self._writer = writer
            self._is_recording = True
            logger.info("Recording started: %s", selected_recording_path)
            return True, "Recording started", filename

    def stop_recording(self) -> Tuple[bool, str]:
        with self._lock:
            if not self._is_recording:
                return True, "Recording is not active"

            self._is_recording = False
            if self._writer is not None:
                self._writer.release()
                self._writer = None
            if self._record_file_handle is not None:
                self._record_file_handle.close()
                self._record_file_handle = None
            self._record_mode = None

            logger.info("Recording stopped")
            return True, "Recording stopped"

    def stop_camera(self) -> Tuple[bool, str]:
        with self._lock:
            if self._capture is None:
                return True, "Camera already stopped"

            self.release_camera()
            return True, "Camera stopped"

    def toggle_face_detection(self) -> bool:
        """Toggle face detection on/off."""
        with self._lock:
            self.face_enabled = self.face_detector.toggle_detection()
            return self.face_enabled

    def toggle_drone_detection(self) -> bool:
        """Toggle drone detection on/off."""
        with self._lock:
            self.drone_enabled = self.drone_detector.toggle_detection()
            return self.drone_enabled

    def toggle_knife_detection(self) -> bool:
        """Toggle knife detection on/off."""
        with self._lock:
            self.knife_enabled = self.weapon_detector.toggle_knife_detection()
            return self.knife_enabled

    def toggle_gun_detection(self) -> bool:
        """Toggle gun detection on/off."""
        with self._lock:
            self.gun_enabled = self.weapon_detector.toggle_gun_detection()
            return self.gun_enabled

    def toggle_weapon_detection(self) -> bool:
        """Backward-compatible combined toggle."""
        with self._lock:
            enabled = self.weapon_detector.toggle_detection()
            self.knife_enabled = enabled
            self.gun_enabled = enabled
            return enabled

    def get_face_detection_status(self) -> Dict[str, object]:
        """Get face detection status."""
        with self._lock:
            return {
                "enabled": self.face_enabled,
                "faces_detected": self.face_detector.get_face_count(),
            }

    def get_drone_detection_status(self) -> Dict[str, object]:
        """Get drone detection status."""
        with self._lock:
            return {
                "enabled": self.drone_enabled,
                "drones_detected": self.drone_detector.get_drone_count(),
            }

    def get_weapon_detection_status(self) -> Dict[str, object]:
        """Get weapon detection status."""
        with self._lock:
            counts = self.weapon_detector.get_weapon_counts()
            return {
                "knife_enabled": self.knife_enabled,
                "gun_enabled": self.gun_enabled,
                "weapon_enabled": self.knife_enabled or self.gun_enabled,
                "gun_available": self.weapon_detector.is_gun_available(),
                "gun_backend": self.weapon_detector.get_gun_backend(),
                "knives_detected": counts["knives_detected"],
                "guns_detected": counts["guns_detected"],
                "total_weapons": counts["total_weapons"],
            }

    def analyze_audio_file(self, file_path: str) -> Dict[str, object]:
        with self._lock:
            return self.audio_drone_detector.detect_file(file_path)

    def get_audio_drone_status(self) -> Dict[str, object]:
        with self._lock:
            return self.audio_drone_detector.get_status()

    def save_audio_detection(self, audio_file_path: str, result: Dict[str, object], source: str = "upload") -> Dict[str, object]:
        with self._lock:
            return self.audio_drone_detector.save_detection(audio_file_path, result, source)

    def get_audio_detection_history(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            return self.audio_drone_detector.get_detection_history(limit)

    def delete_audio_detection(self, filename: str) -> Dict[str, object]:
        with self._lock:
            return self.audio_drone_detector.delete_detection(filename)

    def get_ai_status(self) -> Dict[str, object]:
        """Get combined AI detection status for all models."""
        with self._lock:
            weapon_counts = self.weapon_detector.get_weapon_counts()
            audio_status = self.audio_drone_detector.get_status()
            active_count = sum([self.face_enabled, self.drone_enabled, self.knife_enabled, self.gun_enabled])
            return {
                "face_enabled": self.face_enabled,
                "drone_enabled": self.drone_enabled,
                "knife_enabled": self.knife_enabled,
                "gun_enabled": self.gun_enabled,
                "weapon_enabled": self.knife_enabled or self.gun_enabled,
                "gun_available": self.weapon_detector.is_gun_available(),
                "gun_backend": self.weapon_detector.get_gun_backend(),
                "faces_detected": self.face_detector.get_face_count(),
                "drones_detected": self.drone_detector.get_drone_count(),
                "knives_detected": weapon_counts["knives_detected"],
                "guns_detected": weapon_counts["guns_detected"],
                "total_weapons": weapon_counts["total_weapons"],
                "audio_drone_available": audio_status["available"],
                "audio_drone_last_result": audio_status["last_result"],
                "multi_ai_active": active_count >= 2,
            }

    def get_state(self) -> Dict[str, object]:
        with self._lock:
            weapon_counts = self.weapon_detector.get_weapon_counts()
            audio_status = self.audio_drone_detector.get_status()
            active_count = sum([self.face_enabled, self.drone_enabled, self.knife_enabled, self.gun_enabled])
            return {
                "is_running": self._is_running,
                "is_recording": self._is_recording,
                "active_camera_index": self._active_camera_index,
                "active_camera_name": self._active_camera_name,
                "fps": round(self._current_fps, 2),
                "face_enabled": self.face_enabled,
                "drone_enabled": self.drone_enabled,
                "knife_enabled": self.knife_enabled,
                "gun_enabled": self.gun_enabled,
                "weapon_enabled": self.knife_enabled or self.gun_enabled,
                "gun_available": self.weapon_detector.is_gun_available(),
                "gun_backend": self.weapon_detector.get_gun_backend(),
                "faces_detected": self.face_detector.get_face_count(),
                "drones_detected": self.drone_detector.get_drone_count(),
                "knives_detected": weapon_counts["knives_detected"],
                "guns_detected": weapon_counts["guns_detected"],
                "total_weapons": weapon_counts["total_weapons"],
                "audio_drone_available": audio_status["available"],
                "audio_drone_last_result": audio_status["last_result"],
                "multi_ai_active": active_count >= 2,
            }

    def get_fps(self) -> float:
        with self._lock:
            return round(self._current_fps, 2)


# Global singleton-like manager for the process
camera_manager: Optional[CameraManager] = None


def init_camera_manager(app_config) -> CameraManager:
    global camera_manager
    if camera_manager is None:
        camera_manager = CameraManager(app_config)
    return camera_manager


def frame_generator(manager: CameraManager):
    while True:
        frame = manager.get_encoded_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )
