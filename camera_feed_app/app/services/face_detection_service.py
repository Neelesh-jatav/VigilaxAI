import threading
from typing import List, Tuple

import cv2


class FaceDetectionService:
    @staticmethod
    def _draw_overlay_text(frame, text: str, origin: Tuple[int, int], text_color: Tuple[int, int, int], font_scale: float = 0.7, thickness: int = 2) -> None:
        font = cv2.FONT_HERSHEY_SIMPLEX
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        x, y = origin
        x = max(8, x)
        y = max(text_h + baseline + 8, y)

        top_left = (x - 6, y - text_h - baseline - 6)
        bottom_right = (x + text_w + 6, y + 6)

        cv2.rectangle(frame, top_left, bottom_right, (0, 0, 0), -1)
        cv2.rectangle(frame, top_left, bottom_right, (40, 40, 40), 1)
        cv2.putText(frame, text, (x, y - 2), font, font_scale, text_color, thickness, cv2.LINE_AA)

    def __init__(
        self,
        cascade_path: str | None = None,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: Tuple[int, int] = (30, 30),
        detection_interval: int = 2,
    ) -> None:
        self._lock = threading.RLock()
        self._cascade_path = cascade_path or (cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self._cascade = None

        self._scale_factor = scale_factor
        self._min_neighbors = min_neighbors
        self._min_size = min_size
        self._detection_interval = max(1, detection_interval)

        self._enabled = False
        self._face_count = 0
        self._frame_counter = 0
        self._last_faces: List[Tuple[int, int, int, int]] = []

    def load_model(self) -> bool:
        with self._lock:
            if self._cascade is not None:
                return True

            cascade = cv2.CascadeClassifier(self._cascade_path)
            if cascade.empty():
                self._cascade = None
                return False

            self._cascade = cascade
            return True

    def toggle_detection(self) -> bool:
        with self._lock:
            self._enabled = not self._enabled
            if not self._enabled:
                self._face_count = 0
                self._last_faces = []
            return self._enabled

    def get_face_count(self) -> int:
        with self._lock:
            return int(self._face_count)

    def is_enabled(self) -> bool:
        with self._lock:
            return bool(self._enabled)

    def detect_faces(self, frame, force: bool = False):
        with self._lock:
            enabled = self._enabled
            has_model = self._cascade is not None or self.load_model()
            self._frame_counter += 1

            if enabled and has_model and (force or self._frame_counter % self._detection_interval == 0):
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                detected = self._cascade.detectMultiScale(
                    gray,
                    scaleFactor=self._scale_factor,
                    minNeighbors=self._min_neighbors,
                    minSize=self._min_size,
                )
                self._last_faces = [tuple(face) for face in detected]
                self._face_count = len(self._last_faces)

            if not enabled:
                self._face_count = 0
                self._last_faces = []

            faces_to_draw = list(self._last_faces)
            face_count = self._face_count
            detection_text = "ON" if enabled and has_model else "OFF"

        for (x, y, w, h) in faces_to_draw:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

        frame_h, frame_w = frame.shape[:2]

        faces_label = f"Faces: {face_count}"
        detection_label = f"Detection: {detection_text}"

        faces_size = cv2.getTextSize(faces_label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        faces_origin = (max(10, frame_w - faces_size[0] - 10), 30)

        detection_size = cv2.getTextSize(detection_label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        detection_origin = (max(10, frame_w - detection_size[0] - 10), max(25, frame_h - 12))

        self._draw_overlay_text(frame, faces_label, faces_origin, (255, 255, 120), 0.7, 2)
        self._draw_overlay_text(
            frame,
            detection_label,
            detection_origin,
            (80, 255, 180) if detection_text == "ON" else (130, 160, 255),
            0.7,
            2,
        )

        return frame
