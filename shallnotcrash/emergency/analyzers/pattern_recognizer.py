#!/usr/bin/env python3
"""
Machine Learning Pattern Recognition for Emergency Detection.
FIXED VERSION: Proper emergency detection with anomaly score consideration
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
        
        # FIXED: Emergency detection thresholds
        self.EMERGENCY_ANOMALY_THRESHOLD = 8.0  # If any anomaly score > 8.0, it's an emergency
        self.CRITICAL_ANOMALY_THRESHOLD = 15.0  # If any anomaly score > 15.0, it's critical
        
        # STARTUP GRACE PERIOD: Ignore false positives during initial startup
        self.startup_time = time.time()
        self.STARTUP_GRACE_PERIOD = 15.0  # 15 seconds to stabilize
        self.readings_count = 0
        self.MIN_READINGS_FOR_EMERGENCY = 5  # Need at least 5 readings before declaring emergency
        
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
            
            # FIXED: Better g_load handling - preserve sign and handle extreme values
            if key == 'g_load':
                # Cap extreme values but preserve the magnitude for emergency detection
                if abs(value) > 10.0:  # Extreme g-load indicates serious problem
                    # Normalize extreme values to max range but signal emergency
                    value = 3.0 if value > 0 else -3.0
                else:
                    value = max(-3.0, min(3.0, value))
            
            # Normalize telemetry values to 0-1 range based on expected ranges
            if key == 'rpm':
                features.append(value / 2700.0)
            elif key == 'oil_pressure':
                features.append(value / 100.0)
            elif key == 'oil_temp':
                features.append(value / 300.0)
            elif key == 'cht':
                features.append(value / 500.0)
            elif key == 'egt':
                features.append(value / 1500.0)
            elif key == 'fuel_flow':
                features.append(value / 15.0)
            elif key == 'g_load':
                features.append((value + 3.0) / 6.0)
            elif key == 'vibration':
                features.append(min(value / 1.0, 1.0))
            elif key == 'bus_volts':
                features.append(value / 30.0)
            elif key == 'control_asymmetry':
                features.append(min(value / 5.0, 1.0))
        
        # Add anomaly scores - EXACTLY like training
        for key in self.telemetry_keys:
            score_data = anomaly_scores.get(key)
            if hasattr(score_data, 'normalized_score'):
                features.append(score_data.normalized_score / 5.0)
            else:
                features.append(0.0)
        
        return np.array(features, dtype=float)

    def predict_pattern(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], **kwargs) -> PatternResult:
        """Predict emergency pattern - FIXED VERSION with startup grace period"""
        
        # Increment reading count
        self.readings_count += 1
        elapsed_time = time.time() - self.startup_time
        
        # STARTUP GRACE PERIOD: During first 15 seconds, be more lenient
        if elapsed_time < self.STARTUP_GRACE_PERIOD or self.readings_count < self.MIN_READINGS_FOR_EMERGENCY:
            # Only detect VERY severe emergencies during grace period
            max_anomaly_score = self._get_max_anomaly_score(anomaly_scores)
            
            if max_anomaly_score >= 50.0:  # Only catastrophic failures (like your engine-off scenario)
                return self._handle_critical_anomaly(telemetry, anomaly_scores, max_anomaly_score)
            
            # Otherwise, return stabilizing status
            remaining_time = max(0, self.STARTUP_GRACE_PERIOD - elapsed_time)
            return PatternResult(
                pattern_type=EmergencyPattern.NORMAL,
                confidence=PatternConfidence.MEDIUM,
                probability=0.80,
                contributing_features=[],
                recommended_action=f"System stabilizing... ({remaining_time:.1f}s remaining)"
            )
        
        # NORMAL OPERATION: After grace period, use full detection
        max_anomaly_score = self._get_max_anomaly_score(anomaly_scores)
        
        # Check if we're in truly normal flight (healthy telemetry + low anomaly scores)
        if self._is_healthy_flight(telemetry, max_anomaly_score):
            return PatternResult(
                pattern_type=EmergencyPattern.NORMAL,
                confidence=PatternConfidence.HIGH,
                probability=0.95,
                contributing_features=[],
                recommended_action="Normal flight operations - All systems healthy."
            )
        
        # CRITICAL FIX: If anomaly scores are extremely high, this IS an emergency
        if max_anomaly_score >= self.CRITICAL_ANOMALY_THRESHOLD:
            return self._handle_critical_anomaly(telemetry, anomaly_scores, max_anomaly_score)
        elif max_anomaly_score >= self.EMERGENCY_ANOMALY_THRESHOLD:
            return self._handle_emergency_anomaly(telemetry, anomaly_scores, max_anomaly_score)
        
        # Continue with ML or rule-based prediction
        if self.is_trained:
            return self._ml_prediction(telemetry, anomaly_scores)
        else:
            return self._rule_based_prediction(anomaly_scores)

    def _is_healthy_flight(self, telemetry: Dict[str, float], max_anomaly_score: float) -> bool:
        """Check if aircraft is in healthy flight condition"""
        # If anomaly scores are low, likely healthy
        if max_anomaly_score < 4.0:
            return True
        
        # Check key parameters for normal flight
        rpm = telemetry.get('rpm', 0)
        oil_pressure = telemetry.get('oil_pressure', 0)
        fuel_flow = telemetry.get('fuel_flow', 0)
        bus_volts = telemetry.get('bus_volts', 0)
        
        healthy_conditions = [
            1800 <= rpm <= 2500,           # Normal cruise RPM
            50 <= oil_pressure <= 90,      # Good oil pressure  
            3.0 <= fuel_flow <= 12.0,      # Reasonable fuel flow
            24 <= bus_volts <= 30,         # Electrical system OK
        ]
        
        # If most parameters look healthy AND anomaly scores aren't too high, it's healthy
        return sum(healthy_conditions) >= 3 and max_anomaly_score < 7.0

    def _get_max_anomaly_score(self, anomaly_scores: Dict[str, Any]) -> float:
        """Get the maximum anomaly score from all parameters"""
        max_score = 0.0
        for score_data in anomaly_scores.values():
            if hasattr(score_data, 'normalized_score'):
                max_score = max(max_score, score_data.normalized_score)
            elif isinstance(score_data, dict) and 'score' in score_data:
                max_score = max(max_score, score_data['score'])
        return max_score

    def _handle_critical_anomaly(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], max_score: float) -> PatternResult:
        """Handle critical anomaly scores (> 15.0) - definite emergency"""
        contributing_params = []
        emergency_type = EmergencyPattern.UNKNOWN_EMERGENCY
        
        # Identify the most severe parameters and determine emergency type
        for param, score_data in anomaly_scores.items():
            score = 0.0
            if hasattr(score_data, 'normalized_score'):
                score = score_data.normalized_score
            elif isinstance(score_data, dict) and 'score' in score_data:
                score = score_data['score']
            
            if score >= self.CRITICAL_ANOMALY_THRESHOLD:
                contributing_params.append(param)
        
        # Determine emergency type based on most critical parameter
        if any(param in ['rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'vibration'] for param in contributing_params):
            emergency_type = EmergencyPattern.ENGINE_DEGRADATION
        elif 'fuel_flow' in contributing_params:
            emergency_type = EmergencyPattern.FUEL_LEAK
        elif any(param in ['g_load', 'control_asymmetry'] for param in contributing_params):
            emergency_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif 'bus_volts' in contributing_params:
            emergency_type = EmergencyPattern.ELECTRICAL_FAILURE
        
        # Check for system cascade (multiple critical systems)
        if len(contributing_params) >= 3:
            emergency_type = EmergencyPattern.SYSTEM_CASCADE
        
        return PatternResult(
            pattern_type=emergency_type,
            confidence=PatternConfidence.VERY_HIGH,
            probability=0.95,
            contributing_features=contributing_params,
            anomaly_score=max_score,
            recommended_action=self._get_recommended_action(emergency_type)
        )

    def _handle_emergency_anomaly(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], max_score: float) -> PatternResult:
        """Handle emergency anomaly scores (8.0-15.0) - likely emergency"""
        contributing_params = []
        emergency_type = EmergencyPattern.UNKNOWN_EMERGENCY
        
        for param, score_data in anomaly_scores.items():
            score = 0.0
            if hasattr(score_data, 'normalized_score'):
                score = score_data.normalized_score
            elif isinstance(score_data, dict) and 'score' in score_data:
                score = score_data['score']
            
            if score >= self.EMERGENCY_ANOMALY_THRESHOLD:
                contributing_params.append(param)
        
        # Determine emergency type
        if any(param in ['rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'vibration'] for param in contributing_params):
            emergency_type = EmergencyPattern.ENGINE_DEGRADATION
        elif 'fuel_flow' in contributing_params:
            emergency_type = EmergencyPattern.FUEL_LEAK
        elif any(param in ['g_load', 'control_asymmetry'] for param in contributing_params):
            emergency_type = EmergencyPattern.STRUCTURAL_FATIGUE
        elif 'bus_volts' in contributing_params:
            emergency_type = EmergencyPattern.ELECTRICAL_FAILURE
        
        return PatternResult(
            pattern_type=emergency_type,
            confidence=PatternConfidence.HIGH,
            probability=0.85,
            contributing_features=contributing_params,
            anomaly_score=max_score,
            recommended_action=self._get_recommended_action(emergency_type)
        )

    def _is_simulation_starting_restrictive(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> bool:
        """FIXED: More restrictive simulation startup detection - only when anomaly scores are low"""
        max_anomaly = self._get_max_anomaly_score(anomaly_scores)
        
        # If anomaly scores are high, it's NOT simulation starting
        if max_anomaly > 5.0:
            return False
        
        rpm = telemetry.get('rpm', 0)
        fuel_flow = telemetry.get('fuel_flow', 0)
        oil_temp = telemetry.get('oil_temp', 0)
        cht = telemetry.get('cht', 0)
        egt = telemetry.get('egt', 0)
        
        # More restrictive conditions - all must be true for startup
        startup_conditions = [
            rpm < 500,  # Much lower RPM threshold
            fuel_flow < 1.0,
            oil_temp < 100,  # Higher oil temp threshold
            max_anomaly < 3.0,  # Anomaly scores must be low
            # Must have some reasonable instrument readings
            (cht > 0 or egt > 0)
        ]
        
        return all(startup_conditions)

    def _is_intentional_engine_shutdown_safe(self, telemetry: Dict[str, float]) -> bool:
        """FIXED: More restrictive intentional shutdown detection"""
        rpm = telemetry.get('rpm', 0)
        fuel_flow = telemetry.get('fuel_flow', 0)
        oil_pressure = telemetry.get('oil_pressure', 0)
        oil_temp = telemetry.get('oil_temp', 0)
        
        # Only consider intentional if systems are still functioning normally
        safe_shutdown_indicators = [
            # Clean mixture cutoff with warm engine
            fuel_flow < 0.5 and rpm < 500 and oil_temp > 120,
            # Engine windmilling with good oil system
            rpm < 800 and oil_pressure > 30 and fuel_flow < 1.0 and oil_temp > 100,
        ]
        
        return any(safe_shutdown_indicators)

    def _ml_prediction(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any]) -> PatternResult:
        """ML prediction with better error handling"""
        try:
            # Extract features
            features = self.extract_features(telemetry, anomaly_scores)
            features_reshaped = features.reshape(1, -1)
            
            # Scale features
            features_scaled = self.scaler.transform(features_reshaped)
            
            # Stage 1: Triage (Normal vs Abnormal)
            triage_pred = self.triage_classifier.predict(features_scaled)[0]
            triage_prob = self.triage_classifier.predict_proba(features_scaled)[0]
            
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
            logging.error(f"Error in ML prediction: {e}")
            return self._rule_based_prediction(anomaly_scores)

    def _rule_based_prediction(self, anomaly_scores: Dict[str, Any]) -> PatternResult:
        """Enhanced rule-based prediction with better thresholds"""
        if not anomaly_scores:
            return PatternResult(
                pattern_type=EmergencyPattern.NORMAL,
                confidence=PatternConfidence.HIGH,
                probability=1.0,
                contributing_features=[],
                recommended_action="Continue normal operations."
            )
        
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
            
            if score > 5.0:  # Threshold for contributing parameters
                contributing.append(key)
        
        if max_score < 5.0:
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
        
        # Determine confidence based on score severity
        if max_score >= 20.0:
            confidence = PatternConfidence.VERY_HIGH
            probability = 0.95
        elif max_score >= 15.0:
            confidence = PatternConfidence.HIGH
            probability = 0.85
        elif max_score >= 10.0:
            confidence = PatternConfidence.MEDIUM
            probability = 0.75
        else:
            confidence = PatternConfidence.LOW
            probability = 0.60
        
        return PatternResult(
            pattern_type=pattern_type,
            confidence=confidence,
            probability=probability,
            contributing_features=contributing,
            anomaly_score=max_score,
            recommended_action=self._get_recommended_action(pattern_type)
        )

    def _identify_contributing_features(self, features: np.ndarray) -> List[str]:
        """Identify which features contributed most to the prediction"""
        contributing = []
        num_telemetry_features = len(self.telemetry_keys)
        
        # Check telemetry features (first half)
        for i in range(num_telemetry_features):
            if features[i] > 0.8:
                contributing.append(f"high_{self.telemetry_keys[i]}")
        
        # Check anomaly scores (second half)
        for i in range(num_telemetry_features, len(features)):
            if features[i] > 0.6:
                param_idx = i - num_telemetry_features
                if param_idx < len(self.telemetry_keys):
                    contributing.append(f"anomaly_{self.telemetry_keys[param_idx]}")
        
        return contributing

    def _get_recommended_action(self, pattern: EmergencyPattern) -> str:
        """Get appropriate emergency response"""
        actions = {
            EmergencyPattern.NORMAL: "Continue normal operations.",
            EmergencyPattern.ENGINE_DEGRADATION: "ENGINE EMERGENCY - Reduce power, monitor instruments, prepare for emergency landing.",
            EmergencyPattern.FUEL_LEAK: "FUEL EMERGENCY - Switch tanks if available, land immediately.",
            EmergencyPattern.STRUCTURAL_FATIGUE: "STRUCTURAL EMERGENCY - Reduce speed, avoid abrupt maneuvers, land IMMEDIATELY.",
            EmergencyPattern.ELECTRICAL_FAILURE: "ELECTRICAL FAILURE - Check circuit breakers, load shed non-essential systems.",
            EmergencyPattern.WEATHER_DISTRESS: "ADVERSE WEATHER - Deviate from current path, consider diversion.",
            EmergencyPattern.SYSTEM_CASCADE: "MULTIPLE SYSTEM FAILURE - DECLARE EMERGENCY, land immediately at nearest airport.",
            EmergencyPattern.UNKNOWN_EMERGENCY: "CRITICAL ANOMALY DETECTED - Maintain aircraft control, assess situation, prepare for emergency landing."
        }
        return actions.get(pattern, "Monitor situation and maintain aircraft control.")

# Global instance with fixed path
MODEL_NAME = "c172p_emergency_model_improved.joblib"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
MODEL_PATH = os.path.join(PROJECT_ROOT, 'models', MODEL_NAME)

# Initialize with error handling
try:
    PATTERN_RECOGNIZER = PatternRecognizer(model_path=MODEL_PATH)
except Exception as e:
    logging.error(f"Failed to initialize PatternRecognizer: {e}")
    PATTERN_RECOGNIZER = PatternRecognizer()  # Fallback to rule-based
    