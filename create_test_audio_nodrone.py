import numpy as np
import scipy.io.wavfile as wavfile

# Create a non-drone audio - speech/voice-like frequencies (lower frequencies)
sr = 16000
duration = 3
n_samples = sr * duration

t = np.linspace(0, duration, n_samples)

# Create speech-like frequencies (primarily 200-500Hz band)
signal = (0.3 * np.sin(2 * np.pi * 200 * t) +  # 200 Hz
          0.2 * np.sin(2 * np.pi * 300 * t) +  # 300 Hz
          0.1 * np.sin(2 * np.pi * 400 * t))    # 400 Hz

# Normalize to int16
signal = np.int16(signal * 32767)

# Save as WAV
output_path = r"c:\Users\neele\Downloads\vigilaxAI\audio1\backend\uploads\test_no_drone.wav"
wavfile.write(output_path, sr, signal)

print(f"Created test no-drone WAV file: {output_path}")
print(f"Shape: {signal.shape}, SR: {sr}")
