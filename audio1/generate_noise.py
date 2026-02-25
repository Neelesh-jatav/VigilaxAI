import numpy as np
import soundfile as sf
import os
import sys

OUTPUT_DIR = "dataset/non_drone"
SR = 16000
DURATION = 3
NUM_FILES = 5

try:
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created directory: {OUTPUT_DIR}")

    def generate_white_noise(filename):
        # Generate white noise
        print(f"Generating {filename}...")
        noise = np.random.uniform(-0.1, 0.1, SR * DURATION)
        path = os.path.join(OUTPUT_DIR, filename)
        sf.write(path, noise, SR)
        print(f"Saved {path}")

    def generate_silence(filename):
        # Generate silence (zeros)
        print(f"Generating {filename}...")
        silence = np.zeros(SR * DURATION)
        path = os.path.join(OUTPUT_DIR, filename)
        sf.write(path, silence, SR)
        print(f"Saved {path}")

    print(f"Generating synthetic noise samples in {OUTPUT_DIR}...")

    for i in range(NUM_FILES):
        generate_white_noise(f"white_noise_{i}.wav")

    for i in range(2):
        generate_silence(f"silence_{i}.wav")

    print("Done.")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
