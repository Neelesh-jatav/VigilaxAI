import base64
import json
import logging
import os
import threading
import urllib.request
import urllib.error
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import cv2

logger = logging.getLogger(__name__)


class DroneDetectionService:
    """Roboflow-based drone detector with local YOLO fallback.

    Primary: Uses Roboflow serverless API (no local weights needed).
    Fallback: Uses local YOLO model if API key not configured.
    For true drone detection, Roboflow model is pre-trained on actual drone dataset (95.9% mAP).
    """

    def __init__(
        self,
        model_path: str = "yolov8s.pt",
        confidence_threshold: float = 0.45,
        drone_class_ids: Optional[List[int]] = None,
        detection_interval: int = 2,
        iou_threshold: float = 0.45,
        enable_preprocessing: bool = True,
        roboflow_api_key: str = "",
        roboflow_model_id: str = "drone-dataset-jiusn/1",
        roboflow_size: int = 640,
    ) -> None:
        self._lock = threading.RLock()

        cache_dir = Path.home() / ".cache" / "vigilaxai" / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)

        if not os.path.isabs(model_path) and os.path.sep not in model_path:
            self._model_path = str(cache_dir / model_path)
        else:
            self._model_path = model_path

        self._confidence_threshold = confidence_threshold
        self._drone_class_ids = drone_class_ids or [4]
        self._detection_interval = max(1, detection_interval)
        self._iou_threshold = iou_threshold
        self._enable_preprocessing = enable_preprocessing

        # Roboflow API configuration
        self._roboflow_api_key = roboflow_api_key
        self._roboflow_model_id = roboflow_model_id
        self._roboflow_size = roboflow_size
        self._use_roboflow = bool(roboflow_api_key)

        self._model = None
        self._enabled = False
        self._drone_count = 0
        self._frame_counter = 0
        self._last_detections: List[Tuple[int, int, int, int, float]] = []
        self._detection_history: List[List[Tuple[int, int, int, int, float]]] = []

    def load_model(self) -> bool:
        with self._lock:
            if self._use_roboflow:
                logger.info(
                    "DroneDetectionService: Using Roboflow API (model_id=%s, api_key=%s...)",
                    self._roboflow_model_id,
                    self._roboflow_api_key[:10] + "***" if self._roboflow_api_key else "NOT_SET",
                )
                return True  # No local model loading needed for API

            # Fallback to local YOLO model
            if self._model is not None:
                return True

            try:
                from ultralytics import YOLO

                logger.info("Loading YOLO model from: %s", self._model_path)
                if os.path.exists(self._model_path):
                    logger.info("Using existing model file: %s", self._model_path)
                else:
                    logger.info("Model not found locally, ultralytics will download to cache...")

                model = YOLO(self._model_path)
                if model is None:
                    logger.error("Failed to load YOLO model from %s", self._model_path)
                    return False

                self._model = model
                logger.info(
                    "DroneDetectionService: YOLO model loaded from %s, watching classes %s",
                    self._model_path,
                    self._drone_class_ids,
                )
                return True
            except ImportError as error:
                logger.error("ultralytics package not installed: %s", error)
                return False
            except Exception as error:
                logger.error("Error loading YOLO model: %s", error)
                logger.info(
                    "Tip: Ensure internet access for first-time download, or place weights in: %s",
                    Path(self._model_path).parent,
                )
                return False

    def _roboflow_detect(self, frame) -> List[Tuple[int, int, int, int, float]]:
        """Invoke Roboflow API for drone detection."""
        try:
            # Encode frame to JPEG
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                logger.error("Failed to encode frame for Roboflow API")
                return []

            # Base64 encode
            img_data = base64.b64encode(buffer).decode("utf-8")

            # Build Roboflow API request
            api_url = f"https://detect.roboflow.com/{self._roboflow_model_id}"
            params = f"?api_key={self._roboflow_api_key}&confidence={self._confidence_threshold}&overlap=30"
            full_url = api_url + params

            # Prepare multipart form data with base64 image
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="image.jpg"\r\n'
                f"Content-Type: image/jpeg\r\n\r\n"
            ).encode("utf-8")
            body += base64.b64decode(img_data)
            body += f"\r\n--{boundary}--\r\n".encode("utf-8")

            request = urllib.request.Request(
                full_url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            detections: List[Tuple[int, int, int, int, float]] = []
            if "predictions" in response_data:
                for pred in response_data["predictions"]:
                    x = pred["x"]
                    y = pred["y"]
                    width = pred["width"]
                    height = pred["height"]
                    confidence = pred["confidence"]

                    # Convert from center (x, y, width, height) to corner coords (x1, y1, x2, y2)
                    x1 = max(0, int(x - width / 2))
                    y1 = max(0, int(y - height / 2))
                    x2 = int(x + width / 2)
                    y2 = int(y + height / 2)

                    detections.append((x1, y1, x2, y2, confidence))

            logger.debug("Roboflow API returned %d detections", len(detections))
            return detections

        except urllib.error.HTTPError as e:
            logger.error("Roboflow API HTTP error: %s", e.code)
            return []
        except urllib.error.URLError as e:
            logger.error("Roboflow API connection error: %s", e.reason)
            return []
        except Exception as error:
            logger.error("Error calling Roboflow API: %s", error)
            return []

    def toggle_detection(self) -> bool:
        with self._lock:
            self._enabled = not self._enabled
            if not self._enabled:
                self._drone_count = 0
                self._last_detections = []
                self._detection_history = []
            logger.info("DroneDetectionService: detection %s", "enabled" if self._enabled else "disabled")
            return self._enabled

    def get_drone_count(self) -> int:
        with self._lock:
            return self._drone_count

    def is_enabled(self) -> bool:
        with self._lock:
            return self._enabled

    def detect_drones(self, frame) -> Optional[object]:
        if frame is None:
            return frame

        with self._lock:
            if not self._enabled:
                return self._add_status_overlays(frame, [], False)

            self._frame_counter += 1
            if self._frame_counter % self._detection_interval != 0:
                frame = self._draw_detections(frame, self._last_detections)
                return self._add_status_overlays(frame, self._last_detections, True)

            processed_frame = self._preprocess_frame(frame) if self._enable_preprocessing else frame

            try:
                # Use Roboflow API if configured, otherwise fall back to local YOLO
                if self._use_roboflow:
                    detections = self._roboflow_detect(processed_frame)
                else:
                    # Local YOLO detection
                    if self._model is None:
                        logger.warning("Model not loaded yet, skipping detection")
                        return self._add_status_overlays(frame, [], False)

                    results = self._model(
                        processed_frame,
                        verbose=False,
                        conf=self._confidence_threshold,
                        iou=self._iou_threshold,
                        classes=self._drone_class_ids,
                        max_det=20,
                    )

                    detections: List[Tuple[int, int, int, int, float]] = []
                    for result in results:
                        if not hasattr(result, "boxes"):
                            continue

                        for box in result.boxes:
                            confidence = float(box.conf[0])
                            if confidence < self._confidence_threshold:
                                continue
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            detections.append((x1, y1, x2, y2, confidence))

                detections = self._filter_temporal_noise(detections)
                self._last_detections = detections
                self._drone_count = len(detections)

                frame = self._draw_detections(frame, detections)
                return self._add_status_overlays(frame, detections, True)
            except Exception as error:
                logger.error("Error during drone detection: %s", error)
                return self._add_status_overlays(frame, self._last_detections, True)

    def _preprocess_frame(self, frame):
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            lightness, channel_a, channel_b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            lightness = clahe.apply(lightness)
            merged = cv2.merge([lightness, channel_a, channel_b])
            return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        except Exception:
            return frame

    def _filter_temporal_noise(
        self, detections: List[Tuple[int, int, int, int, float]]
    ) -> List[Tuple[int, int, int, int, float]]:
        if not detections:
            self._detection_history.append([])
            if len(self._detection_history) > 4:
                self._detection_history.pop(0)
            return []

        self._detection_history.append(detections)
        if len(self._detection_history) > 4:
            self._detection_history.pop(0)

        if len(self._detection_history) < 2:
            return detections

        filtered: List[Tuple[int, int, int, int, float]] = []
        previous_frames = self._detection_history[:-1]

        for detection in detections:
            x1, y1, x2, y2, confidence = detection
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            if confidence >= 0.65:
                filtered.append(detection)
                continue

            matched = False
            for frame_detections in previous_frames:
                for previous in frame_detections:
                    px1, py1, px2, py2, _ = previous
                    previous_center_x = (px1 + px2) / 2
                    previous_center_y = (py1 + py2) / 2
                    distance = ((center_x - previous_center_x) ** 2 + (center_y - previous_center_y) ** 2) ** 0.5
                    if distance < 90:
                        matched = True
                        break
                if matched:
                    break

            if matched:
                filtered.append(detection)

        return filtered

    def _draw_detections(self, frame, detections: List[Tuple[int, int, int, int, float]]):
        for x1, y1, x2, y2, confidence in detections:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

            label = f"DRONE {confidence:.2f}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            thickness = 2

            (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(
                frame,
                (x1, y1 - label_h - baseline - 5),
                (x1 + label_w, y1),
                (0, 0, 255),
                -1,
            )
            cv2.putText(
                frame,
                label,
                (x1, y1 - baseline - 5),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA,
            )

        return frame

    def _add_status_overlays(self, frame, detections: List[Tuple[int, int, int, int, float]], is_enabled: bool):
        frame_h, frame_w = frame.shape[:2]

        drone_label = f"Drones: {len(detections)}"
        drone_size = cv2.getTextSize(drone_label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        drone_origin = (max(10, frame_w - drone_size[0] - 10), 65)
        cv2.putText(
            frame,
            drone_label,
            drone_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 0, 255),
            2,
            cv2.LINE_AA,
        )

        status_label = f"Drone: {'ON' if is_enabled else 'OFF'}"
        status_size = cv2.getTextSize(status_label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        status_origin = (max(10, frame_w - status_size[0] - 10), max(25, frame_h - 47))
        cv2.putText(
            frame,
            status_label,
            status_origin,
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 100, 0) if is_enabled else (128, 100, 0),
            2,
            cv2.LINE_AA,
        )

        return frame
