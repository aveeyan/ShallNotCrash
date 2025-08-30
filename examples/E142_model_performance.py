#!/usr/bin/env python3
"""
Example E143: ShallNotCrash Model Evaluation Suite.
(Corrected to handle optimistic misclassifications)
"""
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
import logging

# --- Path Setup ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shallnotcrash.emergency.analyzers.pattern_recognizer import PatternRecognizer, EmergencyPattern
from shallnotcrash.emergency.synthetic_data import generate_training_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION ---
MODEL_FILENAME = "c172p_emergency_model_v2.joblib"
ABSOLUTE_MODEL_PATH = os.path.join(project_root, 'models', MODEL_FILENAME)
TEST_DATA_SAMPLES = 5000
TEST_DATA_SEED = 101
OUTPUT_DIR = os.path.join(project_root, "evaluation_results")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def plot_confusion_matrix(y_true, y_pred, class_enums, title, filename):
    """Generates and saves a styled confusion matrix."""
    class_values = [p.value for p in class_enums]
    class_names = [p.name for p in class_enums]
    
    cm = confusion_matrix(y_true, y_pred, labels=class_values)
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax,
                xticklabels=class_names, yticklabels=class_names)
    ax.set_title(title, fontsize=16, pad=20)
    ax.set_ylabel('True Label', fontsize=12)
    ax.set_xlabel('Predicted Label', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    output_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(output_path)
    logging.info(f"Saved plot to {output_path}")
    plt.close(fig)


def main():
    """Main function to run the evaluation pipeline."""
    logging.info("--- Starting Model Evaluation Suite ---")

    if not os.path.exists(ABSOLUTE_MODEL_PATH):
        logging.error(f"FATAL: Model artifact not found at {ABSOLUTE_MODEL_PATH}. Cannot proceed.")
        logging.error("Please run the training script first: python3 -m shallnotcrash.emergency.training")
        return

    recognizer = PatternRecognizer(model_path=ABSOLUTE_MODEL_PATH)
    if not recognizer.is_trained:
        logging.error("Model failed to load correctly. Aborting evaluation.")
        return

    logging.info(f"Generating {TEST_DATA_SAMPLES} unseen test samples with seed={TEST_DATA_SEED}...")
    test_data = generate_training_data(num_samples=TEST_DATA_SAMPLES, seed=TEST_DATA_SEED)

    logging.info("Running predictions on the test dataset...")
    true_labels = [sample['pattern_label'] for sample in test_data]
    predicted_labels = [recognizer.predict_pattern(s['telemetry'], s.get('anomaly_scores', {})).pattern_type.value for s in test_data]

    # --- Evaluate Triage Performance ---
    logging.info("\n--- Evaluating Stage 1: Triage Classifier ---")
    y_true_triage = [0 if label == EmergencyPattern.NORMAL.value else 1 for label in true_labels]
    y_pred_triage = [0 if label == EmergencyPattern.NORMAL.value else 1 for label in predicted_labels]
    
    class TriageNormal: value=0; name='NORMAL'
    class TriageAbnormal: value=1; name='ABNORMAL'
    triage_enums = [TriageNormal, TriageAbnormal]
    
    print(classification_report(y_true_triage, y_pred_triage, target_names=[p.name for p in triage_enums]))
    plot_confusion_matrix(y_true_triage, y_pred_triage,
                          class_enums=triage_enums,
                          title='Triage Classifier Confusion Matrix (Normal vs. Abnormal)',
                          filename='triage_confusion_matrix.png')

    # --- Evaluate Specialist Performance ---
    logging.info("\n--- Evaluating Stage 2: Specialist Classifier (on emergencies only) ---")
    
    emergency_indices = [i for i, label in enumerate(true_labels) if label != EmergencyPattern.NORMAL.value]
    y_true_specialist = [true_labels[i] for i in emergency_indices]
    y_pred_specialist = [predicted_labels[i] for i in emergency_indices]
    
    specialist_enums = [p for p in EmergencyPattern if p != EmergencyPattern.NORMAL]
    specialist_names = [p.name for p in specialist_enums]
    specialist_values = [p.value for p in specialist_enums]

    # THE FIX: Explicitly provide the 'labels' parameter to tell the function which classes to report on.
    print(classification_report(y_true_specialist, y_pred_specialist, 
                                labels=specialist_values, 
                                target_names=specialist_names, 
                                zero_division=0))
                                
    plot_confusion_matrix(y_true_specialist, y_pred_specialist,
                          class_enums=specialist_enums,
                          title='Specialist Classifier Confusion Matrix (Emergency Types)',
                          filename='specialist_confusion_matrix.png')

    logging.info("--- Evaluation Complete ---")


if __name__ == "__main__":
    main()
