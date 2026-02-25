import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense
from sklearn.model_selection import train_test_split
import os

def train():
    # Load data
    if not os.path.exists("X.npy") or not os.path.exists("y.npy"):
        print("Data not found. Please run process_data.py first.")
        return

    X = np.load("X.npy")
    y = np.load("y.npy")

    print(f"Loaded data: X shape: {X.shape}, y shape: {y.shape}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Input shape
    input_shape = X_train.shape[1:] # (n_mels, time_steps, 1)

    # Build Model
    model = Sequential([
        Conv2D(16, (3, 3), activation='relu', input_shape=input_shape),
        MaxPooling2D((2, 2)),
        Conv2D(32, (3, 3), activation='relu'),
        MaxPooling2D((2, 2)),
        Flatten(),
        Dense(64, activation='relu'),
        Dense(1, activation='sigmoid')
    ])

    model.compile(optimizer='adam',
                  loss='binary_crossentropy',
                  metrics=['accuracy'])

    model.summary()

    # Train
    print("Starting training...")
    history = model.fit(X_train, y_train, epochs=20, validation_data=(X_test, y_test), batch_size=32)

    # Save Model
    model_dir = os.path.join("backend", "model")
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    
    model_path = os.path.join(model_dir, "drone_audio_model.h5")
    model.save(model_path)
    print(f"Model saved to {model_path}")

    # Evaluate
    loss, acc = model.evaluate(X_test, y_test)
    print(f"Test Accuracy: {acc*100:.2f}%")

if __name__ == "__main__":
    train()
