# shallnotcrash/emergency/evaluate_model.py
"""
Model Evaluation Script for the ShallNotCrash Emergency Module.
This script loads a pre-trained model and evaluates its performance on a
fresh, unseen dataset, generating a classification report and a
confusion matrix visualization.
"""
import joblib
import numpy as np
import logging
import os
import sys

from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

# --- Pathing Setup ---
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path: sys.path.insert(0, project_root)
except NameError:
    project_root = os.path.abspath(os.path.join(os.getcwd()))
    if project_root not in sys.path: sys.path.insert(0, project_root)

from shallnotcrash.emergency.synthetic_data import generate_training_data
from shallnotcrash.emergency.analyzers.pattern_recognizer import PatternRecognizer, EmergencyPattern

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
MODEL_DIR = "models"
MODEL_FILENAME = os.path.join(MODEL_DIR, "c172p_emergency_model_v3_tuned.joblib")
NUM_EVAL_SAMPLES = 5000 # Use a different number of samples for evaluation
EVAL_SEED = 123 # Use a different seed from training

def main():
    logging.info("--- Starting Model Performance Evaluation ---")

    # --- 1. Load the Trained Model Artifact ---
    if not os.path.exists(MODEL_FILENAME):
        logging.error(f"Model file not found at '{MODEL_FILENAME}'. Please run training.py first.")
        return
        
    logging.info(f"Loading model from {MODEL_FILENAME}...")
    model_artifact = joblib.load(MODEL_FILENAME)
    scaler = model_artifact['scaler']
    triage_classifier = model_artifact['triage_classifier']
    specialist_classifier = model_artifact['specialist_classifier']

    # --- 2. Generate a Fresh, Unseen Test Dataset ---
    logging.info(f"Generating {NUM_EVAL_SAMPLES} new samples for evaluation...")
    eval_data = generate_training_data(NUM_EVAL_SAMPLES, seed=EVAL_SEED)
    
    feature_extractor = PatternRecognizer()
    features_list = [feature_extractor.extract_features(s['telemetry'], s['anomaly_scores']) for s in eval_data]
    
    X_eval = np.array(features_list)
    y_true = np.array([s['pattern_label'] for s in eval_data])

    # --- 3. Prepare Data and Make Predictions ---
    # IMPORTANT: Use the scaler from the loaded artifact, do NOT fit it again.
    X_eval_scaled = scaler.transform(X_eval)

    logging.info("Making predictions using the two-stage model...")
    # Stage 1: Triage predictions
    triage_preds = triage_classifier.predict(X_eval_scaled)
    
    # Stage 2: Specialist predictions
    final_preds = np.copy(triage_preds) # Start with triage results
    # Find which samples were flagged as ABNORMAL (1)
    abnormal_indices = np.where(triage_preds == 1)[0]
    
    if len(abnormal_indices) > 0:
        # Get the features for only the abnormal samples
        X_abnormal = X_eval_scaled[abnormal_indices]
        # Predict the specific emergency for these samples
        specialist_preds = specialist_classifier.predict(X_abnormal)
        # Place the specialist predictions back into our final prediction array
        # The triage model predicts 0 for NORMAL, while the specialist predicts specific emergency values (2, 3, etc.)
        # To get the final label, we need to map the triage '1' (ABNORMAL) to the actual emergency value.
        # However, for simplicity in evaluation, we will just use the specialist predictions directly.
        
        # A simple way to combine: if triage says normal, it's normal. If abnormal, use specialist.
        # First, convert triage predictions from 0/1 to the actual enum values
        y_pred = np.array([EmergencyPattern.NORMAL.value] * len(y_true))
        specialist_preds = specialist_classifier.predict(X_eval_scaled[abnormal_indices])
        y_pred[abnormal_indices] = specialist_preds

    else:
        y_pred = np.array([EmergencyPattern.NORMAL.value] * len(y_true))


    # --- 4. Calculate and Print Metrics ---
    logging.info("--- Model Performance Report ---")
    
    # Define the labels for the report
    class_labels = [p.value for p in EmergencyPattern]
    class_names = [p.name for p in EmergencyPattern]

    # Overall Accuracy
    accuracy = accuracy_score(y_true, y_pred)
    print(f"\nOverall Accuracy: {accuracy:.4f}\n")

    # Detailed Report (Precision, Recall, F1-Score)
    print("Classification Report:")
    print(classification_report(y_true, y_pred, labels=class_labels, target_names=class_names, zero_division=0))

    # --- 5. Generate and Save Confusion Matrix ---
    logging.info("Generating confusion matrix visualization...")
    cm = confusion_matrix(y_true, y_pred, labels=class_labels)
    
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=class_names, yticklabels=class_names)
    plt.title('Confusion Matrix', fontsize=16)
    plt.ylabel('True Label', fontsize=12)
    plt.xlabel('Predicted Label', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    matrix_filename = "confusion_matrix.png"
    plt.savefig(matrix_filename)
    logging.info(f"Confusion matrix saved to '{matrix_filename}'")
    
if __name__ == '__main__':
    main()
    