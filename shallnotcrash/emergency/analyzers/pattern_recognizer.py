#!/usr/bin/env python3
"""
Machine Learning Pattern Recognition for Emergency Detection.
FINAL VERSION: This module is responsible for loading a pre-trained model
and using it to predict emergency patterns.
(Version 3.0 - Investigative and Definitive)
"""
import numpy as np
import os
import joblib
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import IntEnum

# --- DATA MODELS ---
class EmergencyPattern(IntEnum):
    NORMAL = 0; ENGINE_DEGRADATION = 1; FUEL_LEAK = 2; STRUCTURAL_FATIGUE = 3
    ELECTRICAL_FAILURE = 4; WEATHER_DISTRESS = 5; SYSTEM_CASCADE = 6; UNKNOWN_EMERGENCY = 7

class PatternConfidence(IntEnum):
    LOW = 1; MEDIUM = 2; HIGH = 3; VERY_HIGH = 4

@dataclass
class PatternResult:
    pattern_type: EmergencyPattern; confidence: PatternConfidence; probability: float
    contributing_features: List[str]; time_to_critical: Optional[float] = None
    recommended_action: str = "Monitor situation"; severity_trend: float = 0.0
    anomaly_score: float = 0.0; timestamp: float = field(default_factory=time.time)

# --- ANOMALY DETECTOR PLACEHOLDERS ---
try:
    from .anomaly_detector import AnomalyScore, AnomalySeverity, FlightPhase
except (ImportError, ValueError):
    logging.warning("Could not import full AnomalyDetector models. Using placeholders.")
    class AnomalySeverity(IntEnum): NORMAL=0; ADVISORY=1; WARNING=2; CRITICAL=3; EMERGENCY=4
    class FlightPhase(IntEnum): PREFLIGHT=0; TAXI=1; TAKEOFF=2; CLIMB=3; CRUISE=4; DESCENT=5; LANDING=6; POSTFLIGHT=7
    @dataclass
    class AnomalyScore: parameter: str; value: float; baseline: float; deviation: float; normalized_score: float; is_anomaly: bool; severity: AnomalySeverity; flight_phase: FlightPhase

# --- PATTERN RECOGNIZER CLASS ---
class PatternRecognizer:
    def __init__(self, model_path: Optional[str] = None):
        self.telemetry_keys = ['rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'fuel_flow', 'g_load', 'vibration', 'aileron', 'elevator', 'rudder', 'bus_volts', 'altimeter_setting_hg', 'airspeed_kt', 'wind_speed_kt', 'ambient_density']
        self.scaler = None
        self.classifier = None
        self.is_trained = False
        if model_path:
            self._load_model_artifact(model_path)
        else:
            logging.info("No model path provided. Initialized in rule-based fallback mode.")

    def _load_model_artifact(self, model_path: str):
        """
        Loads the model artifact by investigating its structure instead of assuming it.
        This is the definitive loading mechanism.
        """
        try:
            if not os.path.exists(model_path):
                logging.warning(f"Model artifact not found at {model_path}. Operating in rule-based mode.")
                return

            model_artifact = joblib.load(model_path)

            # --- [THE ULTIMATE FIX] ---
            # We no longer assume the structure. We investigate it.
            # First, check if the artifact is a dictionary, which is the most common case.
            if isinstance(model_artifact, dict):
                # Log the discovered keys. This is critical for any future debugging.
                discovered_keys = list(model_artifact.keys())
                logging.info(f"Model artifact is a dictionary. Discovered keys: {discovered_keys}")

                # Dynamically find the scaler component
                possible_scaler_keys = ['scaler', 'preprocessor', 'feature_transformer']
                scaler_key = next((key for key in possible_scaler_keys if key in model_artifact), None)
                if not scaler_key:
                    raise KeyError(f"Could not find a valid SCALER key in the artifact. Found keys: {discovered_keys}")
                self.scaler = model_artifact[scaler_key]

                # Dynamically find the classifier component
                possible_classifier_keys = ['classifier', 'specialist_classifier', 'model', 'estimator', 'clf', 'predictor']
                classifier_key = next((key for key in possible_classifier_keys if key in model_artifact), None)
                if not classifier_key:
                    raise KeyError(f"Could not find a valid CLASSIFIER key in the artifact. Found keys: {discovered_keys}")
                self.classifier = model_artifact[classifier_key]

                logging.info(f"Successfully loaded scaler ('{scaler_key}') and classifier ('{classifier_key}') from model artifact.")
                self.is_trained = True

            # Second, check if the artifact itself is a scikit-learn Pipeline or a single model
            elif hasattr(model_artifact, 'predict_proba') and hasattr(model_artifact, 'transform'):
                # This looks like a scikit-learn Pipeline object which contains both scaler and classifier.
                logging.info("Model artifact appears to be a scikit-learn Pipeline object.")
                # In a Pipeline, the object handles both scaling and prediction.
                # We can assign the whole pipeline to both roles.
                self.scaler = model_artifact
                self.classifier = model_artifact
                self.is_trained = True
                logging.info("Successfully loaded Pipeline. It will handle both scaling and classification.")
            
            else:
                raise TypeError(f"The loaded model artifact is of an unrecognized type: {type(model_artifact)}. It is not a dictionary or a recognizable model/pipeline.")

        except Exception as e:
            logging.error(f"A definitive failure occurred while loading model from {model_path}. Reason: {e}. Operating in fallback mode.", exc_info=True)
            self.is_trained = False

    def extract_features(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> np.ndarray:
        """Extracts a fixed-size feature vector from input data."""
        telemetry_vector = [telemetry.get(key, 0.0) for key in self.telemetry_keys]
        anomaly_vector = []
        for key in self.telemetry_keys:
            score_data = anomaly_scores.get(key)
            if hasattr(score_data, 'normalized_score'):
                anomaly_vector.append(score_data.normalized_score)
            elif isinstance(score_data, dict) and 'score' in score_data:
                anomaly_vector.append(score_data.get('score', 0.0))
            else:
                anomaly_vector.append(0.0)
        return np.array(telemetry_vector + anomaly_vector, dtype=float)

    def predict_pattern(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], **kwargs) -> PatternResult:
        """Predicts emergency patterns using the loaded model pipeline."""
        if not self.is_trained:
            return self._rule_based_prediction(anomaly_scores)

        features = self.extract_features(telemetry, anomaly_scores)
        features_reshaped = features.reshape(1, -1)
        
        # The scaler and classifier might be the same object (a Pipeline) or separate. This code handles both.
        features_scaled = self.scaler.transform(features_reshaped)
        probabilities = self.classifier.predict_proba(features_scaled)[0]
        
        class_labels = self.classifier.classes_
        best_idx = np.argmax(probabilities)
        pattern_type = EmergencyPattern(class_labels[best_idx])
        confidence_score = probabilities[best_idx]

        if pattern_type == EmergencyPattern.NORMAL:
            return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.VERY_HIGH, probability=confidence_score, contributing_features=[])

        if confidence_score >= 0.9: confidence = PatternConfidence.VERY_HIGH
        elif confidence_score >= 0.75: confidence = PatternConfidence.HIGH
        elif confidence_score >= 0.5: confidence = PatternConfidence.MEDIUM
        else: confidence = PatternConfidence.LOW

        return PatternResult(
            pattern_type=pattern_type,
            confidence=confidence,
            probability=float(confidence_score),
            contributing_features=self._identify_contributing_features(features),
            recommended_action=self._get_recommended_action(pattern_type)
        )

    def _rule_based_prediction(self, anomaly_scores: Dict[str, Any]) -> PatternResult:
        """Fallback prediction for when the ML model is not loaded."""
        if not anomaly_scores: return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=1.0, contributing_features=[])
        max_score, param_name, contributing = 0.0, "", []
        for key, val in anomaly_scores.items():
            score = 0.0
            if hasattr(val, 'normalized_score'): score = val.normalized_score
            elif isinstance(val, dict) and 'score' in val: score = val['score']
            if score > max_score: max_score, param_name = score, key
            if score > 0.4: contributing.append(key)
        if max_score < 0.4: return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=1.0, contributing_features=[])
        pattern_type = EmergencyPattern.UNKNOWN_EMERGENCY
        if param_name in {'rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt'}: pattern_type = EmergencyPattern.ENGINE_DEGRADATION
        elif param_name == 'fuel_flow': pattern_type = EmergencyPattern.FUEL_LEAK
        elif param_name in {'g_load', 'vibration'}: pattern_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif param_name == 'bus_volts': pattern_type = EmergencyPattern.ELECTRICAL_FAILURE
        return PatternResult(pattern_type=pattern_type, confidence=PatternConfidence.MEDIUM, probability=0.5, contributing_features=contributing)

    def _identify_contributing_features(self, features: np.ndarray) -> List[str]:
        """Identifies features with high anomaly scores."""
        anomaly_part = features[len(self.telemetry_keys):]
        return [self.telemetry_keys[i] for i in np.where(anomaly_part > 0.4)[0]]

    def _get_recommended_action(self, pattern: EmergencyPattern) -> str:
        """Returns a recommended action based on the detected pattern."""
        actions = {
            EmergencyPattern.NORMAL: "Continue normal operations.",
            EmergencyPattern.ENGINE_DEGRADATION: "ENGINE ISSUE - Monitor instruments, prepare for precautionary landing.",
            EmergencyPattern.FUEL_LEAK: "FUEL EMERGENCY - Land as soon as possible.",
            EmergencyPattern.STRUCTURAL_FATIGUE: "STRUCTURAL STRESS - Reduce speed and avoid abrupt maneuvers.",
            EmergencyPattern.ELECTRICAL_FAILURE: "ELECTRICAL FAILURE - Check circuit breakers, load shed non-essential systems.",
            EmergencyPattern.WEATHER_DISTRESS: "ADVERSE WEATHER - Deviate from current path, consider diversion.",
            EmergencyPattern.SYSTEM_CASCADE: "MULTIPLE FAILURES - Declare emergency, land immediately.",
            EmergencyPattern.UNKNOWN_EMERGENCY: "UNIDENTIFIED ANOMALY - Maintain aircraft control, assess situation."
        }
        return actions.get(pattern, "Monitor situation.")

# --- SINGLETON INSTANCE CREATION ---
MODEL_NAME = "c172p_pattern_recognizer_v2.joblib"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', MODEL_NAME)
PATTERN_RECOGNIZER = PatternRecognizer(model_path=MODEL_PATH)
