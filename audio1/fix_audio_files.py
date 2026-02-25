import os
from moviepy import AudioFileClip

# Paths
DRONE_DIR = "dataset/drone"

def convert_to_wav():
    print("Checking and converting audio files in dataset/drone...")
    
    for filename in os.listdir(DRONE_DIR):
        if filename.endswith(".mp3"):
            filepath = os.path.join(DRONE_DIR, filename)
            wav_filename = os.path.splitext(filename)[0] + ".wav"
            wav_filepath = os.path.join(DRONE_DIR, wav_filename)
            
            print(f"Converting {filename} to {wav_filename}...")
            
            try:
                # Load audio using moviepy (uses ffmpeg internally)
                clip = AudioFileClip(filepath)
                clip.write_audiofile(wav_filepath, codec='pcm_s16le', logger=None)
                clip.close()
                
                print(f"Success! Removing original file: {filename}")
                os.remove(filepath)
                
            except Exception as e:
                print(f"Failed to convert {filename}: {e}")

if __name__ == "__main__":
    convert_to_wav()
