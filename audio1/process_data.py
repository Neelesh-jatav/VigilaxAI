import os
import numpy as np
from backend.audio_utils import load_and_preprocess_audio, audio_to_mel_spectrogram

# Paths
DATASET_PATH = "dataset"
DRONE_DIR = os.path.join(DATASET_PATH, "drone")
NON_DRONE_DIR = os.path.join(DATASET_PATH, "non_drone")

def process_dataset():
    X = []
    y = []
    
    # Check if directories exist and are not empty
    if not os.path.exists(DRONE_DIR) or not os.listdir(DRONE_DIR):
        print(f"WARNING: No files found in {DRONE_DIR}. Please add drone audio files.")
    
    if not os.path.exists(NON_DRONE_DIR) or not os.listdir(NON_DRONE_DIR):
        print(f"WARNING: No files found in {NON_DRONE_DIR}. Please add non-drone audio files.")

    print("Processing Drone Samples...")
    for filename in os.listdir(DRONE_DIR):
        if filename.endswith(".wav") or filename.endswith(".mp3"):
            path = os.path.join(DRONE_DIR, filename)
            audio = load_and_preprocess_audio(path)
            if audio is not None:
                mel = audio_to_mel_spectrogram(audio)
                X.append(mel)
                y.append(1) # Label 1 for Drone
                print(f"Processed {filename}")

    print("Processing Non-Drone Samples...")
    for filename in os.listdir(NON_DRONE_DIR):
        if filename.endswith(".wav") or filename.endswith(".mp3"):
            path = os.path.join(NON_DRONE_DIR, filename)
            audio = load_and_preprocess_audio(path)
            if audio is not None:
                mel = audio_to_mel_spectrogram(audio)
                X.append(mel)
                y.append(0) # Label 0 for Non-Drone
                print(f"Processed {filename}")

    X = np.array(X)
    y = np.array(y)

    # Check if we have data
    if len(X) == 0:
        print("ERROR: No data processed. Exiting.")
        return

    # Reshape for CNN input: (batch, height, width, channels)
    # Mel spectrogram output shape is (n_mels, time_steps)
    # We add a channel dimension -> (batch, n_mels, time_steps, 1)
    X = X[..., np.newaxis]

    print(f"Dataset shape: {X.shape}")
    print(f"Labels shape: {y.shape}")

    np.save("X.npy", X)
    np.save("y.npy", y)
    print("Data saved to X.npy and y.npy")

if __name__ == "__main__":
    process_dataset()
