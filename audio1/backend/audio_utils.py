import librosa
import numpy as np
import os

# Configuration
TARGET_SR = 16000
DURATION = 3
N_MELS = 128

def load_and_preprocess_audio(path, target_sr=TARGET_SR, duration=DURATION):
    """
    Loads audio, resamples to target_sr, and pads/trims to fixed duration.
    """
    try:
        y, sr = librosa.load(path, sr=target_sr)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return None

    target_length = target_sr * duration
    
    # Trim or Pad
    if len(y) > target_length:
        y = y[:target_length]
    else:
        padding = target_length - len(y)
        y = np.pad(y, (0, padding), mode='constant')
        
    return y

def audio_to_mel_spectrogram(y, sr=TARGET_SR, n_mels=N_MELS):
    """
    Converts audio waveform to Mel Spectrogram (db scale).
    """
    mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels)
    mel_db = librosa.power_to_db(mel, ref=np.max)
    
    # Normalization (optional but recommended for deep learning)
    # This maps values roughly to 0-1 range if we assume min db is around -80
    # For now, we will return the raw db values. The model can handle it or we can normalize later.
    return mel_db

def save_spectrogram_image(mel_db, output_path):
    """
    Saves mel spectrogram as an image (for visualization/debugging).
    """
    import matplotlib.pyplot as plt
    import librosa.display
    
    plt.figure(figsize=(10, 4))
    librosa.display.specshow(mel_db, sr=TARGET_SR, x_axis='time', y_axis='mel')
    plt.colorbar(format='%+2.0f dB')
    plt.title('Mel-frequency spectrogram')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
