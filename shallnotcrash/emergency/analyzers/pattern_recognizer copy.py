# shallnotcrash/emergency/analyzers/pattern_recognizer.py
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
    LOSS_OF_CONTROL = 7
    # [FIX] UNKNOWN_EMERGENCY has been removed.

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

# --- PATTERN RECOGNIZER CLASS ---
class PatternRecognizer:
    def __init__(self, model_path: Optional[str] = None):
        # [FIX] This list now correctly contains all 14 features, matching the trained model.
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
        self.MIN_READINGS_FOR_EMERGENCY = 5
        self.EMERGENCY_ANOMALY_THRESHOLD = 8.0
        self.CRITICAL_ANOMALY_THRESHOLD = 15.0
        
        if model_path and os.path.exists(model_path):
            self._load_model_artifact(model_path)
        else:
            logging.warning(f"Model not found at {model_path}. Using rule-based fallback.")

    def _load_model_artifact(self, model_path: str):
        # ... (no changes in this function) ...
        try:
            model_artifact = joblib.load(model_path)
            if not isinstance(model_artifact, dict):
                logging.error(f"Model artifact is not a dictionary: {type(model_artifact)}")
                return
            self.scaler = model_artifact.get('scaler')
            self.triage_classifier = model_artifact.get('triage_classifier')
            self.specialist_classifier = model_artifact.get('specialist_classifier')
            if all([self.scaler, self.triage_classifier, self.specialist_classifier]):
                self.is_trained = True
                logging.info("Successfully loaded trained model artifact")
            else:
                missing = [k for k,v in {'scaler':self.scaler, 'triage':self.triage_classifier, 'specialist':self.specialist_classifier}.items() if v is None]
                logging.error(f"Missing components in model artifact: {missing}")
        except Exception as e:
            logging.error(f"Failed to load model from {model_path}: {e}")
            self.is_trained = False


    def extract_features(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> np.ndarray:
        # ... (no changes in this function) ...
        features = []
        # This loop now correctly iterates over all 14 keys.
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
            if hasattr(score_data, 'normalized_score'): features.append(score_data.normalized_score / 5.0)
            else: features.append(0.0)
        return np.array(features, dtype=float)


    def predict_pattern(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], **kwargs) -> PatternResult:
        # ... (no changes in this function's logic, but the return types are now constrained) ...
        self.readings_count += 1
        elapsed_time = time.time() - self.startup_time
        if elapsed_time < self.STARTUP_GRACE_PERIOD or self.readings_count < self.MIN_READINGS_FOR_EMERGENCY:
            max_anomaly_score = self._get_max_anomaly_score(anomaly_scores)
            if max_anomaly_score >= 50.0:
                return self._handle_critical_anomaly(telemetry, anomaly_scores, max_anomaly_score)
            remaining_time = max(0, self.STARTUP_GRACE_PERIOD - elapsed_time)
            return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.MEDIUM, probability=0.80,
                                 contributing_features=[], recommended_action=f"System stabilizing... ({remaining_time:.1f}s remaining)")
        
        max_anomaly_score = self._get_max_anomaly_score(anomaly_scores)
        if self._is_healthy_flight(telemetry, max_anomaly_score):
            return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=0.95,
                                 contributing_features=[], recommended_action="Normal flight operations - All systems healthy.")
        
        if max_anomaly_score >= self.CRITICAL_ANOMALY_THRESHOLD:
            return self._handle_critical_anomaly(telemetry, anomaly_scores, max_anomaly_score)
        elif max_anomaly_score >= self.EMERGENCY_ANOMALY_THRESHOLD:
            return self._handle_emergency_anomaly(telemetry, anomaly_scores, max_anomaly_score)
        
        if self.is_trained:
            return self._ml_prediction(telemetry, anomaly_scores)
        else:
            return self._rule_based_prediction(anomaly_scores)

    def _get_max_anomaly_score(self, anomaly_scores: Dict[str, Any]) -> float:
        # ... (no changes in this function) ...
        max_score = 0.0
        for score_data in anomaly_scores.values():
            if hasattr(score_data, 'normalized_score'):
                max_score = max(max_score, score_data.normalized_score)
            elif isinstance(score_data, dict) and 'score' in score_data:
                max_score = max(max_score, score_data['score'])
        return max_score

    def _is_healthy_flight(self, telemetry: Dict[str, float], max_anomaly_score: float) -> bool:
        # ... (no changes in this function) ...
        if max_anomaly_score < 4.0: return True
        rpm = telemetry.get('rpm', 0)
        oil_pressure = telemetry.get('oil_pressure', 0)
        fuel_flow = telemetry.get('fuel_flow', 0)
        bus_volts = telemetry.get('bus_volts', 0)
        healthy_conditions = [1800 <= rpm <= 2500, 50 <= oil_pressure <= 90, 3.0 <= fuel_flow <= 12.0, 24 <= bus_volts <= 30]
        return sum(healthy_conditions) >= 3 and max_anomaly_score < 7.0

    def _handle_critical_anomaly(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], max_score: float) -> PatternResult:
        contributing_params = []
        # [FIX] Default to a more useful emergency type instead of UNKNOWN
        emergency_type = EmergencyPattern.ENGINE_DEGRADATION
        
        for param, score_data in anomaly_scores.items():
            score = score_data.normalized_score if hasattr(score_data, 'normalized_score') else 0.0
            if score >= self.CRITICAL_ANOMALY_THRESHOLD:
                contributing_params.append(param)
        
        if any(param in ['rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'vibration'] for param in contributing_params):
            emergency_type = EmergencyPattern.ENGINE_DEGRADATION
        elif 'fuel_flow' in contributing_params:
            emergency_type = EmergencyPattern.FUEL_LEAK
        elif any(param in ['g_load', 'control_asymmetry'] for param in contributing_params):
            emergency_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif 'bus_volts' in contributing_params:
            emergency_type = EmergencyPattern.ELECTRICAL_FAILURE
        
        if len(contributing_params) >= 3:
            emergency_type = EmergencyPattern.SYSTEM_CASCADE
        
        return PatternResult(pattern_type=emergency_type, confidence=PatternConfidence.VERY_HIGH, probability=0.95,
                             contributing_features=contributing_params, anomaly_score=max_score,
                             recommended_action=self._get_recommended_action(emergency_type))

    def _handle_emergency_anomaly(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], max_score: float) -> PatternResult:
        contributing_params = []
        # [FIX] Default to a more useful emergency type
        emergency_type = EmergencyPattern.ENGINE_DEGRADATION
        
        for param, score_data in anomaly_scores.items():
            score = score_data.normalized_score if hasattr(score_data, 'normalized_score') else 0.0
            if score >= self.EMERGENCY_ANOMALY_THRESHOLD:
                contributing_params.append(param)
        
        if any(param in ['rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'vibration'] for param in contributing_params):
            emergency_type = EmergencyPattern.ENGINE_DEGRADATION
        elif 'fuel_flow' in contributing_params:
            emergency_type = EmergencyPattern.FUEL_LEAK
        elif any(param in ['g_load', 'control_asymmetry'] for param in contributing_params):
            emergency_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif 'bus_volts' in contributing_params:
            emergency_type = EmergencyPattern.ELECTRICAL_FAILURE
            
        return PatternResult(pattern_type=emergency_type, confidence=PatternConfidence.HIGH, probability=0.85,
                             contributing_features=contributing_params, anomaly_score=max_score,
                             recommended_action=self._get_recommended_action(emergency_type))
    
    def _ml_prediction(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> PatternResult:
        # ... (no changes in this function) ...
        try:
            features = self.extract_features(telemetry, anomaly_scores)
            features_reshaped = features.reshape(1, -1)
            features_scaled = self.scaler.transform(features_reshaped)
            triage_pred = self.triage_classifier.predict(features_scaled)[0]
            triage_prob = self.triage_classifier.predict_proba(features_scaled)[0]
            if triage_pred == 0:
                return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.VERY_HIGH, probability=float(triage_prob[0]),
                                     contributing_features=[], recommended_action="Continue normal operations.")
            
            specialist_pred = self.specialist_classifier.predict(features_scaled)[0]
            specialist_prob = self.specialist_classifier.predict_proba(features_scaled)[0]
            confidence_score = max(specialist_prob)
            pattern_type = EmergencyPattern(specialist_pred)
            if confidence_score >= 0.9: confidence = PatternConfidence.VERY_HIGH
            elif confidence_score >= 0.75: confidence = PatternConfidence.HIGH
            elif confidence_score >= 0.5: confidence = PatternConfidence.MEDIUM
            else: confidence = PatternConfidence.LOW
            
            return PatternResult(pattern_type=pattern_type, confidence=confidence, probability=float(confidence_score),
                                 contributing_features=self._identify_contributing_features(features),
                                 recommended_action=self._get_recommended_action(pattern_type))
        except Exception as e:
            logging.error(f"Error in ML prediction: {e}")
            return self._rule_based_prediction(anomaly_scores)


    def _rule_based_prediction(self, anomaly_scores: Dict[str, Any]) -> PatternResult:
        # ... (This function now defaults to ENGINE_DEGRADATION if an issue is found) ...
        if not anomaly_scores: return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=1.0, contributing_features=[], recommended_action="Continue normal operations.")
        max_score, worst_param, contributing = 0.0, "", []
        for key, score_data in anomaly_scores.items():
            score = score_data.normalized_score if hasattr(score_data, 'normalized_score') else 0.0
            if score > max_score: max_score, worst_param = score, key
            if score > 5.0: contributing.append(key)
        
        if max_score < 5.0: return PatternResult(pattern_type=EmergencyPattern.NORMAL, confidence=PatternConfidence.HIGH, probability=1.0, contributing_features=[], recommended_action="Continue normal operations.")
        
        pattern_type = EmergencyPattern.ENGINE_DEGRADATION # [FIX] Default to a more useful emergency type
        if worst_param in {'rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'vibration'}: pattern_type = EmergencyPattern.ENGINE_DEGRADATION
        elif worst_param == 'fuel_flow': pattern_type = EmergencyPattern.FUEL_LEAK
        elif worst_param in {'g_load', 'control_asymmetry'}: pattern_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif worst_param == 'bus_volts': pattern_type = EmergencyPattern.ELECTRICAL_FAILURE
        
        if max_score >= 20.0: confidence, probability = PatternConfidence.VERY_HIGH, 0.95
        elif max_score >= 15.0: confidence, probability = PatternConfidence.HIGH, 0.85
        elif max_score >= 10.0: confidence, probability = PatternConfidence.MEDIUM, 0.75
        else: confidence, probability = PatternConfidence.LOW, 0.60
            
        return PatternResult(pattern_type=pattern_type, confidence=confidence, probability=probability, contributing_features=contributing,
                             anomaly_score=max_score, recommended_action=self._get_recommended_action(pattern_type))

    def _identify_contributing_features(self, features: np.ndarray) -> List[str]:
        # ... (no changes in this function) ...
        contributing = []
        num_telemetry_features = len(self.telemetry_keys)
        for i in range(num_telemetry_features):
            if features[i] > 0.8: contributing.append(f"high_{self.telemetry_keys[i]}")
        for i in range(num_telemetry_features, len(features)):
            if features[i] > 0.6:
                param_idx = i - num_telemetry_features
                if param_idx < len(self.telemetry_keys): contributing.append(f"anomaly_{self.telemetry_keys[param_idx]}")
        return contributing

    def _get_recommended_action(self, pattern: EmergencyPattern) -> str:
        actions = {
            EmergencyPattern.NORMAL: "Continue normal operations.",
            EmergencyPattern.ENGINE_DEGRADATION: "ENGINE EMERGENCY - Reduce power, monitor instruments, prepare for emergency landing.",
            EmergencyPattern.FUEL_LEAK: "FUEL EMERGENCY - Switch tanks if available, land immediately.",
            EmergencyPattern.STRUCTURAL_FATIGUE: "STRUCTURAL EMERGENCY - Reduce speed, avoid abrupt maneuvers, land IMMEDIATELY.",
            EmergencyPattern.ELECTRICAL_FAILURE: "ELECTRICAL FAILURE - Check circuit breakers, load shed non-essential systems.",
            EmergencyPattern.WEATHER_DISTRESS: "ADVERSE WEATHER - Deviate from current path, consider diversion.",
            EmergencyPattern.SYSTEM_CASCADE: "MULTIPLE SYSTEM FAILURE - DECLARE EMERGENCY, land immediately at nearest airport.",
            # [FIX] Removed UNKNOWN_EMERGENCY
        }
        return actions.get(pattern, "Monitor situation and maintain aircraft control.")
