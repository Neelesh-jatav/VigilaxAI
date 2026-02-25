import base64
import json
import logging
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2

logger = logging.getLogger(__name__)

# COCO class IDs used for weapon detection via base YOLOv8 model
KNIFE_COCO_CLASS_ID = 43

# Default colors for drawing
COLOR_KNIFE = (0, 0, 255)      # Red
COLOR_GUN = (255, 0, 0)        # Blue
COLOR_LABEL_BG_KNIFE = (0, 0, 255)
COLOR_LABEL_BG_GUN = (255, 0, 0)
COLOR_TEXT = (255, 255, 255)    # White


class WeaponDetectionService:
    """YOLO-based weapon (knife + gun) detector.

    Uses YOLOv8 base model for knife detection (COCO class 43)
    and an optional custom gun model for gun detection.
    Follows the same modular pattern as DroneDetectionService.
    """

    def __init__(
        self,
        base_model_path: str = "yolov8n.pt",
        gun_model_path: str = "",
        confidence_threshold: float = 0.50,
        detection_interval: int = 3,
        iou_threshold: float = 0.45,
        gun_roboflow_api_key: str = "",
        gun_roboflow_model_id: str = "",
        gun_roboflow_size: int = 640,
    ) -> None:
        self._lock = threading.RLock()

        # Model paths
        cache_dir = Path.home() / ".cache" / "vigilaxai" / "models"
        cache_dir.mkdir(parents=True, exist_ok=True)

        if not os.path.isabs(base_model_path) and os.path.sep not in base_model_path:
            self._base_model_path = str(cache_dir / base_model_path)
        else:
            self._base_model_path = base_model_path

        self._gun_model_path = gun_model_path  # Optional custom gun model
        self._gun_roboflow_api_key = gun_roboflow_api_key
        self._gun_roboflow_model_id = gun_roboflow_model_id
        self._gun_roboflow_size = int(gun_roboflow_size)
        self._gun_use_roboflow = bool(gun_roboflow_api_key and gun_roboflow_model_id)

        self._confidence_threshold = confidence_threshold
        self._detection_interval = max(1, detection_interval)
        self._iou_threshold = iou_threshold

        self._base_model = None
        self._gun_model = None
        self._gun_backend = "none"
        self._knife_enabled = False
        self._gun_enabled = False
        self._knife_count = 0
        self._gun_count = 0
        self._frame_counter = 0
        self._last_knife_detections: List[Tuple[int, int, int, int, float]] = []
        self._last_gun_detections: List[Tuple[int, int, int, int, float]] = []

    def load_model(self) -> bool:
        """Load YOLO models for weapon detection."""
        with self._lock:
            if self._base_model is not None:
                return True

            try:
                from ultralytics import YOLO

                # Load base model for knife detection (COCO class 43)
                logger.info("WeaponDetectionService: Loading base YOLO model from %s", self._base_model_path)
                if os.path.exists(self._base_model_path):
                    logger.info("Using existing base model: %s", self._base_model_path)
                else:
                    logger.info("Base model not found locally, ultralytics will download...")

                self._base_model = YOLO(self._base_model_path)

                # Optionally load custom gun model
                if self._gun_model_path and os.path.exists(self._gun_model_path):
                    logger.info("Loading custom gun model from %s", self._gun_model_path)
                    self._gun_model = YOLO(self._gun_model_path)
                    self._gun_backend = "custom_yolo"
                    logger.info("Gun model loaded successfully")
                elif self._gun_use_roboflow:
                    self._gun_backend = "roboflow"
                    logger.info(
                        "Using Roboflow gun backend (model_id=%s, api_key=%s...)",
                        self._gun_roboflow_model_id,
                        self._gun_roboflow_api_key[:10] + "***" if self._gun_roboflow_api_key else "NOT_SET",
                    )
                else:
                    self._gun_backend = "none"
                    logger.info("No custom gun model configured; gun detection disabled")

                logger.info("WeaponDetectionService: Models loaded (knife=COCO:43, gun=%s)",
                            self._gun_backend)
                return True

            except ImportError as error:
                logger.error("ultralytics package not installed: %s", error)
                return False
            except Exception as error:
                logger.error("Error loading weapon models: %s", error)
                return False

    def toggle_knife_detection(self) -> bool:
        """Toggle knife detection on/off."""
        with self._lock:
            self._knife_enabled = not self._knife_enabled
            if not self._knife_enabled:
                self._knife_count = 0
                self._last_knife_detections = []
            logger.info("WeaponDetectionService: knife detection %s",
                        "enabled" if self._knife_enabled else "disabled")
            return self._knife_enabled

    def toggle_gun_detection(self) -> bool:
        """Toggle gun detection on/off."""
        with self._lock:
            if not self.is_gun_available():
                logger.warning("Gun detection toggle requested but no gun backend is configured")
                self._gun_enabled = False
                self._gun_count = 0
                self._last_gun_detections = []
                return False

            self._gun_enabled = not self._gun_enabled
            if not self._gun_enabled:
                self._gun_count = 0
                self._last_gun_detections = []
            logger.info("WeaponDetectionService: gun detection %s",
                        "enabled" if self._gun_enabled else "disabled")
            return self._gun_enabled

    def disable_all(self) -> None:
        """Disable knife and gun detection and reset counts."""
        with self._lock:
            self._knife_enabled = False
            self._gun_enabled = False
            self._knife_count = 0
            self._gun_count = 0
            self._last_knife_detections = []
            self._last_gun_detections = []

    def toggle_detection(self) -> bool:
        """Backward-compatible toggle for combined weapon detection."""
        with self._lock:
            new_state = not (self._knife_enabled or self._gun_enabled)
            self._knife_enabled = new_state
            self._gun_enabled = new_state
            if not new_state:
                self._knife_count = 0
                self._gun_count = 0
                self._last_knife_detections = []
                self._last_gun_detections = []
            logger.info("WeaponDetectionService: detection %s",
                        "enabled" if new_state else "disabled")
            return new_state

    def get_weapon_counts(self) -> Dict[str, int]:
        """Return current knife and gun counts."""
        with self._lock:
            return {
                "knives_detected": self._knife_count,
                "guns_detected": self._gun_count,
                "total_weapons": self._knife_count + self._gun_count,
            }

    def get_knife_count(self) -> int:
        with self._lock:
            return self._knife_count

    def get_gun_count(self) -> int:
        with self._lock:
            return self._gun_count

    def is_knife_enabled(self) -> bool:
        with self._lock:
            return self._knife_enabled

    def is_gun_enabled(self) -> bool:
        with self._lock:
            return self._gun_enabled

    def is_gun_available(self) -> bool:
        with self._lock:
            return self._gun_backend != "none"

    def get_gun_backend(self) -> str:
        with self._lock:
            return self._gun_backend

    def is_enabled(self) -> bool:
        with self._lock:
            return self._knife_enabled or self._gun_enabled

    def detect_weapons(self, frame) -> Optional[object]:
        """Run weapon detection on frame. Returns annotated frame."""
        if frame is None:
            return frame

        with self._lock:
            if not self._knife_enabled and not self._gun_enabled:
                return self._add_status_overlays(frame)

            if self._knife_enabled and self._base_model is None:
                return self._add_status_overlays(frame, False)

            self._frame_counter += 1
            if self._frame_counter % self._detection_interval != 0:
                # Reuse previous detections on skipped frames
                frame = self._draw_detections(frame)
                return self._add_status_overlays(frame)

            try:
                # --- Knife detection via base YOLO model (COCO class 43) ---
                knife_detections: List[Tuple[int, int, int, int, float]] = []
                if self._knife_enabled:
                    knife_results = self._base_model(
                        frame,
                        verbose=False,
                        conf=self._confidence_threshold,
                        iou=self._iou_threshold,
                        classes=[KNIFE_COCO_CLASS_ID],
                        max_det=20,
                    )

                    for result in knife_results:
                        if not hasattr(result, "boxes"):
                            continue
                        for box in result.boxes:
                            confidence = float(box.conf[0])
                            if confidence >= self._confidence_threshold:
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                knife_detections.append((x1, y1, x2, y2, confidence))

                self._last_knife_detections = knife_detections
                self._knife_count = len(knife_detections)

                # --- Gun detection via custom model (if loaded) ---
                gun_detections: List[Tuple[int, int, int, int, float]] = []
                if self._gun_enabled:
                    if self._gun_backend == "custom_yolo" and self._gun_model is not None:
                        gun_results = self._gun_model(
                            frame,
                            verbose=False,
                            conf=self._confidence_threshold,
                            iou=self._iou_threshold,
                            max_det=20,
                        )
                        for result in gun_results:
                            if not hasattr(result, "boxes"):
                                continue
                            for box in result.boxes:
                                confidence = float(box.conf[0])
                                if confidence >= self._confidence_threshold:
                                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                                    gun_detections.append((x1, y1, x2, y2, confidence))
                    elif self._gun_backend == "roboflow":
                        gun_detections = self._roboflow_detect_gun(frame)

                self._last_gun_detections = gun_detections
                self._gun_count = len(gun_detections)

                frame = self._draw_detections(frame)
                return self._add_status_overlays(frame)

            except Exception as error:
                logger.error("Error during weapon detection: %s", error)
                return self._add_status_overlays(frame)

    def _roboflow_detect_gun(self, frame) -> List[Tuple[int, int, int, int, float]]:
        """Invoke Roboflow API for gun detection and apply NMS cleanup."""
        try:
            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                return []

            api_url = f"https://detect.roboflow.com/{self._gun_roboflow_model_id}"
            params = f"?api_key={self._gun_roboflow_api_key}&confidence={self._confidence_threshold}&overlap=35"
            full_url = api_url + params

            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; filename="image.jpg"\r\n'
                f"Content-Type: image/jpeg\r\n\r\n"
            ).encode("utf-8")
            body += base64.b64decode(base64.b64encode(buffer).decode("utf-8"))
            body += f"\r\n--{boundary}--\r\n".encode("utf-8")

            request = urllib.request.Request(
                full_url,
                data=body,
                method="POST",
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )

            with urllib.request.urlopen(request, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))

            raw_detections: List[Tuple[int, int, int, int, float]] = []
            for pred in response_data.get("predictions", []):
                confidence = float(pred.get("confidence", 0.0))
                if confidence < self._confidence_threshold:
                    continue
                x = float(pred.get("x", 0))
                y = float(pred.get("y", 0))
                width = float(pred.get("width", 0))
                height = float(pred.get("height", 0))

                x1 = max(0, int(x - width / 2))
                y1 = max(0, int(y - height / 2))
                x2 = int(x + width / 2)
                y2 = int(y + height / 2)
                raw_detections.append((x1, y1, x2, y2, confidence))

            if not raw_detections:
                return []

            nms_boxes = []
            scores = []
            for x1, y1, x2, y2, conf in raw_detections:
                nms_boxes.append([x1, y1, max(1, x2 - x1), max(1, y2 - y1)])
                scores.append(float(conf))

            kept_indexes = cv2.dnn.NMSBoxes(
                nms_boxes,
                scores,
                self._confidence_threshold,
                self._iou_threshold,
            )

            if kept_indexes is None or len(kept_indexes) == 0:
                return []

            filtered: List[Tuple[int, int, int, int, float]] = []
            for idx in kept_indexes:
                resolved = int(idx[0]) if isinstance(idx, (list, tuple)) else int(idx)
                filtered.append(raw_detections[resolved])

            return filtered
        except urllib.error.HTTPError as error:
            logger.error("Gun Roboflow API HTTP error: %s", error.code)
            return []
        except urllib.error.URLError as error:
            logger.error("Gun Roboflow API connection error: %s", error.reason)
            return []
        except Exception as error:
            logger.error("Gun Roboflow detection error: %s", error)
            return []

    def _draw_detections(self, frame):
        """Draw knife and gun bounding boxes and labels on frame."""
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2

        # Draw knife detections (red)
        for x1, y1, x2, y2, conf in self._last_knife_detections:
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_KNIFE, 2)
            label = f"Knife - {conf:.2f}"
            (lw, lh), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(frame, (x1, y1 - lh - baseline - 5), (x1 + lw, y1), COLOR_LABEL_BG_KNIFE, -1)
            cv2.putText(frame, label, (x1, y1 - baseline - 5), font, font_scale, COLOR_TEXT, thickness, cv2.LINE_AA)

        # Draw gun detections (blue)
        for x1, y1, x2, y2, conf in self._last_gun_detections:
            cv2.rectangle(frame, (x1, y1), (x2, y2), COLOR_GUN, 2)
            label = f"Gun - {conf:.2f}"
            (lw, lh), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(frame, (x1, y1 - lh - baseline - 5), (x1 + lw, y1), COLOR_LABEL_BG_GUN, -1)
            cv2.putText(frame, label, (x1, y1 - baseline - 5), font, font_scale, COLOR_TEXT, thickness, cv2.LINE_AA)

        return frame

    def _add_status_overlays(self, frame, has_explicit_state: Optional[bool] = None):
        """Add weapon count and status overlays to frame."""
        frame_h, frame_w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX

        total = self._knife_count + self._gun_count

        # Top right - weapon counts (below drone overlay area)
        weapon_label = f"Weapons: {total}"
        weapon_size = cv2.getTextSize(weapon_label, font, 0.7, 2)[0]
        weapon_origin = (max(10, frame_w - weapon_size[0] - 10), 90)
        cv2.putText(frame, weapon_label, weapon_origin, font, 0.7, (0, 100, 255), 2, cv2.LINE_AA)

        if self._knife_count > 0:
            knife_label = f"Knives: {self._knife_count}"
            knife_size = cv2.getTextSize(knife_label, font, 0.55, 2)[0]
            cv2.putText(frame, knife_label, (max(10, frame_w - knife_size[0] - 10), 115),
                        font, 0.55, COLOR_KNIFE, 2, cv2.LINE_AA)

        if self._gun_count > 0:
            gun_label = f"Guns: {self._gun_count}"
            gun_size = cv2.getTextSize(gun_label, font, 0.55, 2)[0]
            cv2.putText(frame, gun_label, (max(10, frame_w - gun_size[0] - 10), 140),
                        font, 0.55, COLOR_GUN, 2, cv2.LINE_AA)

        # Bottom status
        if has_explicit_state is None:
            is_enabled = self._knife_enabled or self._gun_enabled
        else:
            is_enabled = has_explicit_state

        status_label = f"Knife: {'ON' if self._knife_enabled else 'OFF'} | Gun: {'ON' if self._gun_enabled else 'OFF'}"
        status_size = cv2.getTextSize(status_label, font, 0.7, 2)[0]
        status_origin = (max(10, frame_w - status_size[0] - 10), max(25, frame_h - 17))
        cv2.putText(frame, status_label, status_origin, font, 0.7,
                    (0, 100, 255) if is_enabled else (128, 100, 0), 2, cv2.LINE_AA)

        return frame
