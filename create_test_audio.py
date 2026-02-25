import numpy as np
import scipy.io.wavfile as wavfile

# Create a synthetic audio waveform - a drone-like sound with 1000Hz + 2000Hz components
sr = 16000
duration = 3
n_samples = sr * duration

t = np.linspace(0, duration, n_samples)

# Create a 'drone-like' sound with multiple frequency components
signal = (0.3 * np.sin(2 * np.pi * 1000 * t) +  # 1 kHz
          0.2 * np.sin(2 * np.pi * 2000 * t) +  # 2 kHz
          0.1 * np.sin(2 * np.pi * 500 * t))      # 500 Hz

# Normalize to int16
signal = np.int16(signal * 32767)

# Save as WAV
output_path = r"c:\Users\neele\Downloads\vigilaxAI\audio1\backend\uploads\test_drone.wav"
wavfile.write(output_path, sr, signal)

print(f"Created test WAV file: {output_path}")
print(f"Shape: {signal.shape}, SR: {sr}")
