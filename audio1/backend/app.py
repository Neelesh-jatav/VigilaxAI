import os
import numpy as np
import tensorflow as tf
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from audio_utils import load_and_preprocess_audio, audio_to_mel_spectrogram

app = Flask(__name__)

# Configuration
MODEL_PATH = os.path.join("backend", "model", "drone_audio_model.h5")
UPLOAD_FOLDER = os.path.join("backend", "uploads")
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global model variable
model = None

def load_model():
    global model
    try:
        # Check if model exists
        if os.path.exists(MODEL_PATH):
            model = tf.keras.models.load_model(MODEL_PATH)
            print("Model loaded successfully!")
        else:
            print(f"Model not found at {MODEL_PATH}. Please train the model first.")
            model = None
    except Exception as e:
        print(f"Error loading model: {e}")
        model = None

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        if model is None:
             return jsonify({'error': 'Model not loaded. Please train the model first.'}), 500

        # Process audio
        try:
            # Load and preprocess
            audio = load_and_preprocess_audio(filepath)
            if audio is None:
                return jsonify({'error': 'Could not process audio file'}), 400
            
            # Convert to Mel Spectrogram
            mel = audio_to_mel_spectrogram(audio)
            
            # Reshape for model (batch, height, width, channels)
            # mel shape is (n_mels, time_steps) -> (1, n_mels, time_steps, 1)
            X = mel[np.newaxis, ..., np.newaxis]
            
            # Predict
            prediction = model.predict(X)
            score = float(prediction[0][0])
            
            label = "Drone Detected" if score > 0.5 else "No Drone"
            confidence = score if score > 0.5 else 1 - score
            
            result = {
                'prediction': label,
                'confidence': f"{confidence:.2f}",
                'raw_score': score
            }
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    load_model()
    # In production, debug should be False
    app.run(debug=True, port=5000)
