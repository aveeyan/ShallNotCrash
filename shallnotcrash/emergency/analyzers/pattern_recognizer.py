# shallnotcrash/emergency/analyzers/pattern_recognizer.py
import numpy as np
import os
import joblib
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import IntEnum

class EmergencyPattern(IntEnum):
    NORMAL = 0
    ENGINE_DEGRADATION = 1
    FUEL_LEAK = 2 
    STRUCTURAL_FATIGUE = 3
    ELECTRICAL_FAILURE = 4
    WEATHER_DISTRESS = 5
    SYSTEM_CASCADE = 6
    LOSS_OF_CONTROL = 7

class PatternConfidence(IntEnum):
    LOW = 1; MEDIUM = 2; HIGH = 3; VERY_HIGH = 4

@dataclass
class PatternResult:
    pattern_type: EmergencyPattern; confidence: PatternConfidence; probability: float
    contributing_features: List[str]; timestamp: float = field(default_factory=time.time)
    recommended_action: str = "Monitor situation"

class PatternRecognizer:
    def __init__(self, model_path: Optional[str] = None):
        self.telemetry_keys = [
            'rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'fuel_flow', 
            'g_load', 'vibration', 'bus_volts', 'control_asymmetry',
            'airspeed', 'yaw_rate', 'roll', 'pitch'
        ]
        self.scaler = None
        self.triage_classifier = None
        self.specialist_classifier = None
        self.is_trained = False
        
        self.startup_time = time.time()
        self.STARTUP_GRACE_PERIOD = 15.0
        self.readings_count = 0
        # [NEW] Define the post-grace stabilization window (10 readings = ~5 seconds)
        self.STABILIZATION_READINGS = 10
        
        if model_path and os.path.exists(model_path):
            self._load_model_artifact(model_path)
        else:
            logging.warning(f"Model not found at {model_path}. Using rule-based fallback.")

    def _load_model_artifact(self, model_path: str):
        try:
            model_artifact = joblib.load(model_path)
            self.scaler = model_artifact.get('scaler')
            self.triage_classifier = model_artifact.get('triage_classifier')
            self.specialist_classifier = model_artifact.get('specialist_classifier')
            if all([self.scaler, self.triage_classifier, self.specialist_classifier]):
                self.is_trained = True
                logging.info("Successfully loaded trained model artifact")
        except Exception as e:
            logging.error(f"Failed to load model from {model_path}: {e}")

    def extract_features(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> np.ndarray:
        features = []
        for key in self.telemetry_keys:
            value = telemetry.get(key, 0.0)
            if key == 'rpm': features.append(value / 2700.0)
            elif key == 'oil_pressure': features.append(value / 100.0)
            elif key == 'oil_temp': features.append(value / 300.0)
            elif key == 'cht': features.append(value / 500.0)
            elif key == 'egt': features.append(value / 1500.0)
            elif key == 'fuel_flow': features.append(value / 15.0)
            elif key == 'g_load': features.append((value + 3.0) / 6.0)
            elif key == 'vibration': features.append(min(value / 1.0, 1.0))
            elif key == 'bus_volts': features.append(value / 30.0)
            elif key == 'control_asymmetry': features.append(min(value / 5.0, 1.0))
            elif key == 'airspeed': features.append(value / 200.0)
            elif key == 'yaw_rate': features.append(value / 180.0)
            elif key == 'roll': features.append(value / 180.0)
            elif key == 'pitch': features.append(value / 90.0)
            else: features.append(0.0)
        
        for key in self.telemetry_keys:
            score_data = anomaly_scores.get(key)
            if hasattr(score_data, 'normalized_score'):
                features.append(score_data.normalized_score / 5.0)
            else: features.append(0.0)
        
        return np.array(features, dtype=float)

    def predict_pattern(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> Optional[PatternResult]:
        self.readings_count += 1
        
        if not self.is_trained:
            return self._rule_based_prediction(anomaly_scores)

        # Let the ML model make its prediction first
        result = self._ml_prediction(telemetry, anomaly_scores)
        if not result:
             return self._rule_based_prediction(anomaly_scores)

        # [FIX] Add a post-grace stabilization window to prevent initial false positives.
        is_in_stabilization_window = self.readings_count < self.STABILIZATION_READINGS

        # If we are in the stabilization window AND the prediction is a low-confidence emergency...
        if is_in_stabilization_window and result.pattern_type != EmergencyPattern.NORMAL and result.probability < 0.75:
            # ...override the result and force it to NORMAL for this cycle.
            logging.info(f"Suppressing low-confidence emergency ({result.pattern_type.name}) during post-grace stabilization.")
            return PatternResult(
                pattern_type=EmergencyPattern.NORMAL,
                confidence=PatternConfidence.HIGH,
                probability=0.90,
                contributing_features=[],
                recommended_action="System stabilizing..."
            )

        # Otherwise, return the original prediction from the model.
        return result

    def _ml_prediction(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> Optional[PatternResult]:
        try:
            features = self.extract_features(telemetry, anomaly_scores)
            if features.shape[0] != self.scaler.n_features_in_:
                 logging.error(f"Feature mismatch! Expected {self.scaler.n_features_in_}, got {features.shape[0]}.")
                 return None
            
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            triage_pred = self.triage_classifier.predict(features_scaled)[0]
            if triage_pred == 0:
                prob = self.triage_classifier.predict_proba(features_scaled)[0][0]
                return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=float(prob), contributing_features=[])
            
            specialist_pred = self.specialist_classifier.predict(features_scaled)[0]
            specialist_probs = self.specialist_classifier.predict_proba(features_scaled)[0]
            confidence_score = np.max(specialist_probs)
            pattern_type = EmergencyPattern(specialist_pred)
            
            return PatternResult(
                pattern_type=pattern_type,
                confidence=self._get_confidence(confidence_score),
                probability=float(confidence_score),
                contributing_features=[],
                recommended_action=self.get_recommended_action(pattern_type)
            )
        except Exception as e:
            logging.error(f"Error in ML prediction: {e}", exc_info=True)
            return None

    def _rule_based_prediction(self, anomaly_scores: Dict[str, Any]) -> PatternResult:
        # ... (no changes in this fallback function) ...
        max_score, worst_param = 0, ""
        for param, score_obj in anomaly_scores.items():
            if score_obj.normalized_score > max_score:
                max_score, worst_param = score_obj.normalized_score, param
        if max_score < 5.0:
            return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=0.9, contributing_features=[])
        pattern = EmergencyPattern.ENGINE_DEGRADATION
        if worst_param in ('yaw_rate', 'roll', 'g_load'): pattern = EmergencyPattern.LOSS_OF_CONTROL
        elif worst_param == 'fuel_flow': pattern = EmergencyPattern.FUEL_LEAK
        return PatternResult(pattern_type=pattern, confidence=PatternConfidence.MEDIUM, probability=0.75, contributing_features=[worst_param], recommended_action=self.get_recommended_action(pattern))

    def _get_confidence(self, probability: float) -> PatternConfidence:
        # ... (no changes) ...
        if probability >= 0.9: return PatternConfidence.VERY_HIGH
        if probability >= 0.75: return PatternConfidence.HIGH
        if probability >= 0.5: return PatternConfidence.MEDIUM
        return PatternConfidence.LOW

    def get_recommended_action(self, pattern: EmergencyPattern) -> str:
        # ... (no changes) ...
        actions = {
            EmergencyPattern.NORMAL: "Continue normal operations.",
            EmergencyPattern.ENGINE_DEGRADATION: "ENGINE EMERGENCY - Reduce power, monitor instruments, prepare for emergency landing.",
            EmergencyPattern.FUEL_LEAK: "FUEL EMERGENCY - Switch tanks if available, land immediately.",
            EmergencyPattern.STRUCTURAL_FATIGUE: "STRUCTURAL EMERGENCY - Reduce speed, avoid abrupt maneuvers, land IMMEDIATELY.",
            EmergencyPattern.ELECTRICAL_FAILURE: "ELECTRICAL FAILURE - Check circuit breakers, load shed non-essential systems.",
            EmergencyPattern.WEATHER_DISTRESS: "ADVERSE WEATHER - Deviate from current path, consider diversion.",
            EmergencyPattern.SYSTEM_CASCADE: "MULTIPLE SYSTEM FAILURE - DECLARE EMERGENCY, land immediately at nearest airport.",
            EmergencyPattern.LOSS_OF_CONTROL: "LOSS OF CONTROL - PARE: Power idle, Ailerons neutral, Rudder opposite, Elevator forward."
        }
        return actions.get(pattern, "Monitor situation and maintain aircraft control.")
    