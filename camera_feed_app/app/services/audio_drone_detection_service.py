import logging
import traceback
import json
import shutil
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


logger = logging.getLogger(__name__)


class AudioDroneDetectionService:
    def __init__(
        self,
        model_path: str,
        confidence_threshold: float = 0.5,
        target_sr: int = 16000,
        duration_seconds: int = 3,
        n_mels: int = 128,
        captures_dir: str = "app/static/captures",
    ) -> None:
        self._model_path = Path(model_path)
        self._confidence_threshold = confidence_threshold
        self._target_sr = target_sr
        self._duration_seconds = duration_seconds
        self._n_mels = n_mels
        self._captures_dir = Path(captures_dir)
        self._detections_log = self._captures_dir / "audio_detections.json"

        self._model = None
        self._available = False
        self._last_result: Optional[Dict[str, object]] = None
        
        # Create captures directory if it doesn't exist
        self._captures_dir.mkdir(parents=True, exist_ok=True)

    def load_model(self) -> bool:
        try:
            import tensorflow as tf
        except Exception as error:
            logger.warning("Audio drone model unavailable: tensorflow import failed (%s)", error)
            self._available = False
            return False

        if not self._model_path.exists():
            logger.warning("Audio drone model file not found: %s", self._model_path)
            self._available = False
            return False

        try:
            self._model = tf.keras.models.load_model(str(self._model_path))
            self._available = True
            logger.info("AudioDroneDetectionService: model loaded from %s", self._model_path)
            return True
        except Exception as error:
            logger.error("Failed to load audio drone model: %s", error)
            self._available = False
            self._model = None
            return False

    def is_available(self) -> bool:
        return self._available and self._model is not None

    def detect_file(self, file_path: str) -> Dict[str, object]:
        if not self.is_available():
            return {
                "success": False,
                "available": False,
                "message": "Audio drone model is unavailable (missing model or dependencies)",
            }

        try:
            import librosa
            import numpy as np
            import scipy.io.wavfile as wavfile
        except Exception as error:
            logger.warning("Audio drone detection unavailable: librosa/numpy/scipy import failed (%s)", error)
            return {
                "success": False,
                "available": False,
                "message": "Audio dependencies are unavailable",
            }

        try:
            logger.info("Loading audio file: %s (sr=%d)", file_path, self._target_sr)
            
            # Check file magic bytes to determine actual format
            with open(file_path, 'rb') as f:
                magic_bytes = f.read(4)
            
            # RIFF WAV files start with 'RIFF'
            is_wav_file = magic_bytes[:4] == b'RIFF'
            
            # Try using scipy for actual WAV files (doesn't need ffmpeg/audioread backend)
            if is_wav_file:
                sr_native, audio_data = wavfile.read(file_path)
                # Convert stereo to mono if needed
                if len(audio_data.shape) > 1:
                    audio_waveform = audio_data.mean(axis=1)
                else:
                    audio_waveform = audio_data
                # Normalize to [-1, 1] if int16
                if audio_waveform.dtype == np.int16:
                    audio_waveform = audio_waveform.astype(np.float32) / 32768.0
                # Resample if necessary
                if sr_native != self._target_sr:
                    from scipy import signal as sp_signal
                    ratio = self._target_sr / sr_native
                    num_samples = int(len(audio_waveform) * ratio)
                    audio_waveform = sp_signal.resample(audio_waveform, num_samples)
            else:
                # Fall back to librosa for other formats
                audio_waveform, _ = librosa.load(file_path, sr=self._target_sr)
            
            logger.info("Audio file loaded successfully, waveform shape: %s", audio_waveform.shape)

            target_length = self._target_sr * self._duration_seconds
            if len(audio_waveform) > target_length:
                audio_waveform = audio_waveform[:target_length]
            elif len(audio_waveform) < target_length:
                padding = target_length - len(audio_waveform)
                audio_waveform = np.pad(audio_waveform, (0, padding), mode="constant")

            mel = librosa.feature.melspectrogram(
                y=audio_waveform,
                sr=self._target_sr,
                n_mels=self._n_mels,
            )
            mel_db = librosa.power_to_db(mel, ref=np.max)

            model_input = mel_db[np.newaxis, ..., np.newaxis]
            prediction = self._model.predict(model_input, verbose=0)
            score = float(prediction[0][0])

            detected = score > self._confidence_threshold
            confidence = score if detected else 1.0 - score

            result = {
                "success": True,
                "available": True,
                "detected": detected,
                "prediction": "Drone Detected" if detected else "No Drone",
                "confidence": round(confidence, 4),
                "raw_score": round(score, 4),
            }
            self._last_result = result
            return result
        except Exception as error:
            logger.error("Audio drone detection failed: %s", error, exc_info=True)
            logger.error("Traceback: %s", traceback.format_exc())
            return {
                "success": False,
                "available": True,
                "message": str(error),
            }

    def get_status(self) -> Dict[str, object]:
        return {
            "available": self.is_available(),
            "last_result": self._last_result,
        }

    def save_detection(self, audio_file_path: str, result: Dict[str, object], source: str = "upload") -> Dict[str, object]:
        """Save detected audio file and metadata to captures directory."""
        try:
            if not result.get("detected", False) or not result.get("success", False):
                return {"success": False, "message": "No detection to save"}

            timestamp = datetime.now()
            filename = f"drone_audio_{timestamp.strftime('%Y%m%d_%H%M%S')}.wav"
            saved_path = self._captures_dir / filename

            # Copy audio file to captures
            shutil.copy2(audio_file_path, saved_path)

            # Create metadata
            detection_metadata = {
                "timestamp": timestamp.isoformat(),
                "filename": filename,
                "source": source,
                "confidence": result.get("confidence"),
                "raw_score": result.get("raw_score"),
                "prediction": result.get("prediction"),
            }

            # Load existing detections log
            detections = self._load_detections_log()
            detections.append(detection_metadata)

            # Save updated log
            self._save_detections_log(detections)

            logger.info(f"Saved drone detection: {filename}")
            return {
                "success": True,
                "filename": filename,
                "path": str(saved_path),
                "metadata": detection_metadata,
            }

        except Exception as error:
            logger.error(f"Failed to save detection: {error}", exc_info=True)
            return {"success": False, "message": str(error)}

    def _load_detections_log(self) -> List[Dict]:
        """Load detections log from JSON file."""
        if not self._detections_log.exists():
            return []
        try:
            with open(self._detections_log, 'r') as f:
                return json.load(f)
        except Exception as error:
            logger.error(f"Failed to load detections log: {error}")
            return []

    def _save_detections_log(self, detections: List[Dict]) -> None:
        """Save detections log to JSON file."""
        try:
            with open(self._detections_log, 'w') as f:
                json.dump(detections, f, indent=2)
        except Exception as error:
            logger.error(f"Failed to save detections log: {error}")

    def get_detection_history(self, limit: int = 50) -> List[Dict]:
        """Get recent detection history."""
        detections = self._load_detections_log()
        # Return most recent first
        return list(reversed(detections[-limit:]))

    def delete_detection(self, filename: str) -> Dict[str, object]:
        """Delete a saved detection."""
        try:
            file_path = self._captures_dir / filename
            if file_path.exists():
                file_path.unlink()

            # Remove from log
            detections = self._load_detections_log()
            detections = [d for d in detections if d.get("filename") != filename]
            self._save_detections_log(detections)

            return {"success": True, "message": f"Deleted {filename}"}
        except Exception as error:
            logger.error(f"Failed to delete detection: {error}")
            return {"success": False, "message": str(error)}
