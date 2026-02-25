# Drone Audio Detection Project

## Project Structure
```
.
├── backend/
│   ├── model/          # Saved models
│   ├── static/         # CSS/JS for frontend
│   ├── templates/      # HTML templates
│   ├── uploads/        # Temp storage for uploaded audio
│   ├── app.py          # Flask application
│   └── audio_utils.py  # Audio processing helper functions
├── dataset/
│   ├── drone/          # Put drone audio files here (.wav)
│   └── non_drone/      # Put background noise/other audio here
├── requirements.txt    # Python dependencies
├── process_data.py     # Script to process audio into dataset
├── train_model.py      # Script to train the CNN model
└── README.md           # This file
```

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Prepare Dataset:**
    *   Collect drone audio samples and place them in `dataset/drone/`.
    *   Collect non-drone audio samples (birds, traffic, silence) and place them in `dataset/non_drone/`.
    *   Ensure files are in `.wav` format (though librosa handles most formats).

3.  **Process Data:**
    Run the processing script to convert audio files into spectrograms for training.
    ```bash
    python process_data.py
    ```
    This will create `X.npy` and `y.npy`.

4.  **Train Model:**
    Train the CNN model.
    ```bash
    python train_model.py
    ```
    This will save the trained model to `backend/model/drone_audio_model.h5`.

5.  **Run Web App:**
    Start the Flask server.
    ```bash
    python backend/app.py
    ```
    Open your browser at `http://localhost:5000`.

## Features
*   **Deep Learning:** Uses a Convolutional Neural Network (CNN) trained on Mel Spectrograms.
*   **Web Interface:** Upload audio files or use microphone (if implemented) to detect drones.
*   **Real-time Capable:** Designed for short audio chunks (3 seconds).
