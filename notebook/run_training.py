#!/usr/bin/env python3
"""
Training script for the ShallNotCrash Emergency Pattern Recognizer.
"""
import logging
import os
import sys

# --- PATHING SETUP ---
# Ensures the script can find the 'shallnotcrash' package.
project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- IMPORTS ---
from ..shallnotcrash.emergency.synthetic_data import generate_training_data
from ..shallnotcrash.emergency.analyzers.pattern_recognizer import PATTERN_RECOGNIZER

# --- CONFIGURATION ---
NUM_TRAINING_SAMPLES = 10000
MODEL_DIR = os.path.join(project_root, 'models')
MODEL_FILENAME = "c172p_pattern_recognizer_v1.joblib"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)

def main():
    """Main training function."""
    logging.info("--- Starting Emergency Pattern Recognizer Training Protocol ---")

    # --- Step 1: Ensure model directory exists ---
    if not os.path.exists(MODEL_DIR):
        logging.info(f"Model directory not found. Creating directory at: {MODEL_DIR}")
        os.makedirs(MODEL_DIR)

    # --- Step 2: Generate Training Data ---
    logging.info(f"Generating {NUM_TRAINING_SAMPLES} samples for training...")
    training_data = generate_training_data(NUM_TRAINING_SAMPLES, include_all_emergencies=True)
    logging.info("Training data generation complete.")

    # --- Step 3: Train the Models ---
    logging.info("Passing data to the Pattern Recognizer for training...")
    # The train_models method is part of the PatternRecognizer class
    PATTERN_RECOGNIZER.train_models(training_data)
    logging.info("Model training complete.")

    # --- Step 4: Save the Trained Models ---
    logging.info(f"Saving trained model artifact to: {MODEL_PATH}")
    PATTERN_RECOGNIZER.save_models(MODEL_PATH)
    logging.info("--- Training Protocol Finished Successfully ---")

if __name__ == "__main__":
    main()