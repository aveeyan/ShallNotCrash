#!/usr/bin/env python3
"""
Machine Learning Pattern Recognition for Emergency Detection.
FINAL VERSION: This module is responsible for loading a pre-trained, two-stage 
model and using it to predict emergency patterns. It does not contain training logic.
(Version 2.3 - Unified Scaler)
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
    NORMAL = 0
    ENGINE_DEGRADATION = 1
    FUEL_LEAK = 2
    STRUCTURAL_FATIGUE = 3
    ELECTRICAL_FAILURE = 4
    WEATHER_DISTRESS = 5
    SYSTEM_CASCADE = 6
    UNKNOWN_EMERGENCY = 7

class PatternConfidence(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

@dataclass
class PatternResult:
    pattern_type: EmergencyPattern
    confidence: PatternConfidence
    probability: float
    contributing_features: List[str]
    time_to_critical: Optional[float] = None
    recommended_action: str = "Monitor situation"
    severity_trend: float = 0.0
    anomaly_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

# --- ANOMALY DETECTOR PLACEHOLDERS ---
try:
    from ..analyzers.anomaly_detector import AnomalyScore, AnomalySeverity, FlightPhase
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
        self.feature_names = self.telemetry_keys + [key + '_anomaly' for key in self.telemetry_keys]

        # THE FIX: Use a single, unified scaler
        self.scaler = None
        self.triage_classifier = None
        self.specialist_classifier = None
        self.is_trained = False

        if model_path:
            self._load_model_artifact(model_path)
        else:
            logging.info("No model path provided. Initialized in rule-based fallback mode.")

    def _load_model_artifact(self, model_path: str):
        """Loads the UNIFIED model artifact from a provided absolute path."""
        try:
            if os.path.exists(model_path):
                model_artifact = joblib.load(model_path)
                # THE FIX: Load the single, unified scaler
                self.scaler = model_artifact['scaler']
                self.triage_classifier = model_artifact['triage_classifier']
                self.specialist_classifier = model_artifact['specialist_classifier']
                self.is_trained = True
                logging.info(f"Successfully loaded unified-scaler model from {model_path}")
            else:
                logging.warning(f"Model artifact not found at {model_path}. Operating in rule-based mode.")
        except Exception as e:
            logging.error(f"Failed to load model from {model_path}: {e}. Operating in fallback mode.", exc_info=True)
            self.is_trained = False

    def extract_features(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> np.ndarray:
        """Extracts a fixed-size, 32-element feature vector from input data."""
        telemetry_vector = [telemetry.get(key, 0.0) for key in self.telemetry_keys]
        anomaly_vector = [anomaly_scores.get(key).normalized_score if anomaly_scores.get(key) else 0.0 for key in self.telemetry_keys]
        return np.array(telemetry_vector + anomaly_vector, dtype=float)

    def predict_pattern(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], **kwargs) -> PatternResult:
        """Predicts emergency patterns using the full two-stage pipeline with a unified scaler."""
        if not self.is_trained:
            return self._rule_based_prediction(anomaly_scores)

        features = self.extract_features(telemetry, anomaly_scores)
        
        # THE FIX: Use the single, unified scaler for all operations
        features_scaled = self.scaler.transform(features.reshape(1, -1))

        # --- STAGE 1: Triage ---
        triage_prediction = self.triage_classifier.predict(features_scaled)[0]

        if triage_prediction == 0: # Model predicts NORMAL
            return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.VERY_HIGH, probability=1.0, contributing_features=[])

        # --- STAGE 2: Specialist Diagnosis ---
        # The features are already scaled correctly. No second scaling is needed.
        probabilities = self.specialist_classifier.predict_proba(features_scaled)[0]
        
        class_labels = self.specialist_classifier.classes_
        best_idx = np.argmax(probabilities)
        pattern_type = EmergencyPattern(class_labels[best_idx])
        confidence_score = probabilities[best_idx]

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
        if not anomaly_scores or not any(s.is_anomaly for s in anomaly_scores.values()):
            return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=1.0, contributing_features=[])
        most_severe_anomaly = max(anomaly_scores.values(), key=lambda s: s.severity.value, default=None)
        param_name = most_severe_anomaly.parameter if most_severe_anomaly else ""
        pattern_type = EmergencyPattern.UNKNOWN_EMERGENCY
        if param_name in {'rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt'}: pattern_type = EmergencyPattern.ENGINE_DEGRADATION
        elif param_name == 'fuel_flow': pattern_type = EmergencyPattern.FUEL_LEAK
        elif param_name in {'g_load', 'vibration'}: pattern_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif param_name == 'bus_volts': pattern_type = EmergencyPattern.ELECTRICAL_FAILURE
        contributing = [name for name, score in anomaly_scores.items() if score.is_anomaly]
        return PatternResult(pattern_type=pattern_type, confidence=PatternConfidence.MEDIUM, probability=0.5, contributing_features=contributing)

    def _identify_contributing_features(self, features: np.ndarray) -> List[str]:
        anomaly_part = features[len(self.telemetry_keys):]
        significant_indices = np.where(anomaly_part > 0.4)[0] # Threshold for being an anomaly
        return [self.telemetry_keys[i] for i in significant_indices]

    def _get_recommended_action(self, pattern: EmergencyPattern) -> str:
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
    