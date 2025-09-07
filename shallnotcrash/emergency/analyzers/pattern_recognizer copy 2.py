# shallnotcrash/emergency/analyzers/pattern_recognizer.py

#!/usr/bin/env python3
"""
Machine Learning Pattern Recognition for Emergency Detection.
REFACTORED VERSION: Fixed model loading and feature extraction
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

# --- PATTERN RECOGNIZER CLASS ---
class PatternRecognizer:
    def __init__(self, model_path: Optional[str] = None):
        self.telemetry_keys = ['rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'fuel_flow', 
                              'g_load', 'vibration', 'bus_volts', 'control_asymmetry']
        self.scaler = None
        self.triage_classifier = None
        self.specialist_classifier = None
        self.is_trained = False
        
        if model_path and os.path.exists(model_path):
            self._load_model_artifact(model_path)
        else:
            logging.warning(f"Model not found at {model_path}. Using rule-based fallback.")
            self.is_trained = False

    def _load_model_artifact(self, model_path: str):
        """Load the trained model artifact with proper error handling"""
        try:
            model_artifact = joblib.load(model_path)
            
            if not isinstance(model_artifact, dict):
                logging.error(f"Model artifact is not a dictionary: {type(model_artifact)}")
                return
                
            # Extract components from the artifact
            self.scaler = model_artifact.get('scaler')
            self.triage_classifier = model_artifact.get('triage_classifier')
            self.specialist_classifier = model_artifact.get('specialist_classifier')
            
            if all([self.scaler, self.triage_classifier, self.specialist_classifier]):
                self.is_trained = True
                logging.info("Successfully loaded trained model artifact")
            else:
                missing = []
                if not self.scaler: missing.append('scaler')
                if not self.triage_classifier: missing.append('triage_classifier')
                if not self.specialist_classifier: missing.append('specialist_classifier')
                logging.error(f"Missing components in model artifact: {missing}")
                
        except Exception as e:
            logging.error(f"Failed to load model from {model_path}: {e}")
            self.is_trained = False

    def extract_features(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> np.ndarray:
        """Extract features for the ML model - FIXED VERSION"""
        features = []
        
        # Add telemetry values (normalized) - EXACTLY like training
        for key in self.telemetry_keys:
            value = telemetry.get(key, 0.0)
            # Normalize telemetry values to 0-1 range based on expected ranges
            if key == 'rpm':
                features.append(value / 2700.0)  # Max RPM 2700
            elif key == 'oil_pressure':
                features.append(value / 100.0)   # Max oil pressure ~80-100
            elif key == 'oil_temp':
                features.append(value / 300.0)   # Max oil temp ~250-300
            elif key == 'cht':
                features.append(value / 500.0)   # Max CHT ~450-500
            elif key == 'egt':
                features.append(value / 1500.0)  # Max EGT ~1400-1500
            elif key == 'fuel_flow':
                features.append(value / 15.0)    # Max fuel flow ~12-15 GPH
            elif key == 'g_load':
                features.append((value + 3.0) / 6.0)  # Normalize -3 to +3 G
            elif key == 'vibration':
                features.append(min(value / 1.0, 1.0))  # Max vibration 1.0
            elif key == 'bus_volts':
                features.append(value / 30.0)    # Normalize 0-30V
            elif key == 'control_asymmetry':
                features.append(min(value / 5.0, 1.0))  # Max asymmetry 5.0
        
        # Add anomaly scores - EXACTLY like training
        for key in self.telemetry_keys:
            score_data = anomaly_scores.get(key)
            if hasattr(score_data, 'normalized_score'):
                features.append(score_data.normalized_score / 5.0)  # Normalize 0-5 scale to 0-1
            else:
                features.append(0.0)  # Missing value
        
        return np.array(features, dtype=float)

    def predict_pattern(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], **kwargs) -> PatternResult:
        """Predict emergency pattern using two-stage classification"""
        if not self.is_trained:
            return self._rule_based_prediction(anomaly_scores)
        
        try:
            # Extract features
            features = self.extract_features(telemetry, anomaly_scores)
            features_reshaped = features.reshape(1, -1)
            
            # Scale features
            features_scaled = self.scaler.transform(features_reshaped)
            
            # Stage 1: Triage (Normal vs Abnormal)
            triage_pred = self.triage_classifier.predict(features_scaled)[0]
            triage_prob = self.triage_classifier.predict_proba(features_scaled)[0]  # FIXED: Use features_scaled
            
            if triage_pred == 0:  # Normal
                return PatternResult(
                    pattern_type=EmergencyPattern.NORMAL,
                    confidence=PatternConfidence.VERY_HIGH,
                    probability=float(triage_prob[0]),
                    contributing_features=[],
                    recommended_action="Continue normal operations."
                )
            
            # Stage 2: Specialist (Specific emergency type)
            specialist_pred = self.specialist_classifier.predict(features_scaled)[0]
            specialist_prob = self.specialist_classifier.predict_proba(features_scaled)[0]
            
            confidence_score = max(specialist_prob)
            pattern_type = EmergencyPattern(specialist_pred)
            
            # Determine confidence level
            if confidence_score >= 0.9:
                confidence = PatternConfidence.VERY_HIGH
            elif confidence_score >= 0.75:
                confidence = PatternConfidence.HIGH
            elif confidence_score >= 0.5:
                confidence = PatternConfidence.MEDIUM
            else:
                confidence = PatternConfidence.LOW
            
            return PatternResult(
                pattern_type=pattern_type,
                confidence=confidence,
                probability=float(confidence_score),
                contributing_features=self._identify_contributing_features(features),
                recommended_action=self._get_recommended_action(pattern_type)
            )
            
        except Exception as e:
            logging.error(f"Error in pattern prediction: {e}")
            return self._rule_based_prediction(anomaly_scores)

    def _rule_based_prediction(self, anomaly_scores: Dict[str, Any]) -> PatternResult:
        """Fallback rule-based prediction"""
        if not anomaly_scores:
            return PatternResult(
                pattern_type=EmergencyPattern.NORMAL,
                confidence=PatternConfidence.HIGH,
                probability=1.0,
                contributing_features=[],
                recommended_action="Continue normal operations."
            )
        
        # Find the most severe anomaly
        max_score = 0.0
        worst_param = ""
        contributing = []
        
        for key, score_data in anomaly_scores.items():
            score = 0.0
            if hasattr(score_data, 'normalized_score'):
                score = score_data.normalized_score
            elif isinstance(score_data, dict) and 'score' in score_data:
                score = score_data['score']
            
            if score > max_score:
                max_score = score
                worst_param = key
            
            if score > 2.0:  # Significant anomaly threshold
                contributing.append(key)
        
        if max_score < 2.0:
            return PatternResult(
                pattern_type=EmergencyPattern.NORMAL,
                confidence=PatternConfidence.HIGH,
                probability=1.0,
                contributing_features=[],
                recommended_action="Continue normal operations."
            )
        
        # Map parameter to emergency type
        pattern_type = EmergencyPattern.UNKNOWN_EMERGENCY
        
        if worst_param in {'rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'vibration'}:
            pattern_type = EmergencyPattern.ENGINE_DEGRADATION
        elif worst_param == 'fuel_flow':
            pattern_type = EmergencyPattern.FUEL_LEAK
        elif worst_param in {'g_load', 'control_asymmetry'}:
            pattern_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif worst_param == 'bus_volts':
            pattern_type = EmergencyPattern.ELECTRICAL_FAILURE
        
        return PatternResult(
            pattern_type=pattern_type,
            confidence=PatternConfidence.MEDIUM,
            probability=0.6,
            contributing_features=contributing,
            recommended_action=self._get_recommended_action(pattern_type)
        )

    def _identify_contributing_features(self, features: np.ndarray) -> List[str]:
        """Identify which features contributed most to the prediction"""
        contributing = []
        num_telemetry_features = len(self.telemetry_keys)
        
        # Check telemetry features (first half)
        for i in range(num_telemetry_features):
            if features[i] > 0.8:  # Highly abnormal telemetry value
                contributing.append(f"high_{self.telemetry_keys[i]}")
        
        # Check anomaly scores (second half)
        for i in range(num_telemetry_features, len(features)):
            if features[i] > 0.6:  # Significant anomaly score
                param_idx = i - num_telemetry_features
                if param_idx < len(self.telemetry_keys):  # Safety check
                    contributing.append(f"anomaly_{self.telemetry_keys[param_idx]}")
        
        return contributing

    def _get_recommended_action(self, pattern: EmergencyPattern) -> str:
        """Get appropriate emergency response"""
        actions = {
            EmergencyPattern.NORMAL: "Continue normal operations.",
            EmergencyPattern.ENGINE_DEGRADATION: "ENGINE ISSUE - Reduce power, monitor instruments, prepare for precautionary landing.",
            EmergencyPattern.FUEL_LEAK: "FUEL EMERGENCY - Switch tanks if available, land as soon as possible.",
            EmergencyPattern.STRUCTURAL_FATIGUE: "STRUCTURAL STRESS - Reduce speed, avoid abrupt maneuvers, land ASAP.",
            EmergencyPattern.ELECTRICAL_FAILURE: "ELECTRICAL FAILURE - Check circuit breakers, load shed non-essential systems.",
            EmergencyPattern.WEATHER_DISTRESS: "ADVERSE WEATHER - Deviate from current path, consider diversion.",
            EmergencyPattern.SYSTEM_CASCADE: "MULTIPLE FAILURES - Declare emergency, land immediately at nearest suitable airport.",
            EmergencyPattern.UNKNOWN_EMERGENCY: "UNIDENTIFIED ANOMALY - Maintain aircraft control, assess instruments, prepare for emergency landing."
        }
        return actions.get(pattern, "Monitor situation and maintain aircraft control.")

# Global instance
MODEL_NAME = "c172p_emergency_model_improved.joblib"  # FIXED: Use correct model name
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', MODEL_NAME)

# Initialize with error handling
try:
    PATTERN_RECOGNIZER = PatternRecognizer(model_path=MODEL_PATH)
except Exception as e:
    logging.error(f"Failed to initialize PatternRecognizer: {e}")
    PATTERN_RECOGNIZER = PatternRecognizer()  # Fallback to rule-based
    