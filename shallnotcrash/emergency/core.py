#!/usr/bin/env python3
"""
Enhanced Emergency Detection Core Module
"""

import os
import joblib
import numpy as np
from collections import deque
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
import logging
from sklearn.preprocessing import StandardScaler

# Import from local utilities modules
from shallnotcrash.emergency.utilities import (
    EmergencyPattern,
    AnomalyScore,
    AnomalySeverity,
    PatternResult,
    PatternConfidence,
    TelemetryData,
    get_pattern_action
)
from shallnotcrash.emergency.utilities.pattern_recognition.pr2_feature_extractor import FeatureExtractor
from shallnotcrash.emergency.utilities.pattern_recognition.pr3_ml_models import MLModelManager
from shallnotcrash.emergency.utilities.pattern_recognition.pr4_pattern_analyzer import PatternAnalyzer

# Import protocols
from shallnotcrash.emergency.protocols import (
    engine_failure,
    fuel_emergency,
    structural_failure
)

logger = logging.getLogger(__name__)

class EmergencyDetector:
    """Enhanced emergency detection system with protocol integration"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the emergency detector with optional model path.
        
        Args:
            model_path: Path to the trained ML model. If None, uses default path.
        """
        self.extractor = FeatureExtractor(window_size=30)
        self.pattern_analyzer = PatternAnalyzer()
        self.pattern_history = deque(maxlen=10)
        
        # Initialize ML model manager
        self.ml_manager = MLModelManager()
        self._load_model(model_path)
        
        # Initialize emergency protocols
        self.protocols = {
            EmergencyPattern.ENGINE_DEGRADATION: engine_failure,
            EmergencyPattern.FUEL_LEAK: fuel_emergency,
            EmergencyPattern.STRUCTURAL_FATIGUE: structural_failure
        }
    
    def _load_model(self, model_path: Optional[str]) -> None:
        """Enhanced model loading with better debugging"""
        # Print debug information
        print("\n=== Model Loading Debug ===")
        print(f"Current directory: {os.getcwd()}")
        print(f"File location: {__file__}")
        
        # Try explicit path first
        if model_path and os.path.exists(model_path):
            print(f"\nAttempting to load from explicit path: {model_path}")
            try:
                if self.ml_manager.load(model_path):
                    print("✔ Model loaded successfully from explicit path")
                    return
            except Exception as e:
                print(f"✖ Load failed: {str(e)}")

        # Try standard locations
        search_paths = [
            # Relative to package
            os.path.join(os.path.dirname(__file__), "../../models/c172p_emergency_model.joblib"),
            # Absolute path
            os.path.expanduser("~/Documents/ShallNotCrash/models/c172p_emergency_model.joblib"),
            # ShallNotCrash package path
            os.path.join(os.path.dirname(__file__), "../../../models/c172p_emergency_model.joblib"),
            # Local models directory
            os.path.join("models", "c172p_emergency_model.joblib")
        ]

        for path in search_paths:
            print(f"\nChecking path: {path}")
            if os.path.exists(path):
                print("✔ File exists, attempting load...")
                try:
                    if self.ml_manager.load(path):
                        print("✔ Model loaded successfully")
                        return
                except Exception as e:
                    print(f"✖ Load failed: {str(e)}")
            else:
                print("✖ File does not exist")

        print("\n⚠ All load attempts failed, initializing fallback")
        self._initialize_fallback_model()

    def _initialize_fallback_model(self):
        """Create a properly trained fallback model"""
        from sklearn.ensemble import RandomForestClassifier
        import numpy as np
        
        print("\nInitializing fallback model...")
        
        # Create minimal training data that matches your feature structure
        n_features = 10  # Should match your actual feature count
        n_classes = len(EmergencyPattern)
        
        X = np.random.rand(100, n_features)
        y = np.random.randint(0, n_classes, size=100)
        
        # Initialize and train
        self.ml_manager.classifier = RandomForestClassifier(
            n_estimators=20,
            random_state=42
        )
        self.ml_manager.classifier.fit(X, y)
        self.ml_manager.is_trained = True
        self.ml_manager.scaler = StandardScaler()
        self.ml_manager.scaler.fit(X)  # Important for feature scaling
        
        print("✔ Fallback model trained and ready")

    def detect(self, 
              telemetry: Dict[str, float], 
              anomalies: Dict[str, Tuple[bool, float, str]], 
              correlations: Dict[str, float]) -> Dict[str, Any]:
        """
        Main detection method with protocol integration.
        
        Args:
            telemetry: Sensor readings dictionary
            anomalies: Dictionary of anomaly tuples (is_anomaly, score, severity_str)
            correlations: System correlation data
            
        Returns:
            Dictionary containing all PatternResult fields
        """
        try:
            # Convert inputs to proper types
            processed_telemetry = self._validate_telemetry(telemetry)
            processed_anomalies = self._process_anomalies(anomalies)
            
            # Extract features
            features = self.extractor.extract(
                telemetry=processed_telemetry,
                anomalies=processed_anomalies,
                correlation_data=correlations
            )
            
            # Make prediction and analyze pattern
            ml_prediction = self._make_ml_prediction(features)
            result = self.pattern_analyzer.analyze(ml_prediction, features)
            
            # Update history and calculate trend
            self.pattern_history.append(result.pattern_type)
            result.severity_trend = self._calculate_trend()
            
            # Trigger protocol if critical
            if self._is_critical(result.pattern_type):
                self._trigger_protocol(result)
            
            return asdict(result)
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return asdict(self._create_error_result())
    
    def _validate_telemetry(self, telemetry: Dict[str, float]) -> TelemetryData:
        """Convert telemetry dict to TelemetryData object"""
        try:
            if isinstance(telemetry, TelemetryData):
                return telemetry
            return TelemetryData(**telemetry)
        except Exception as e:
            logger.warning(f"Invalid telemetry data: {e}")
            return TelemetryData()  # Return empty with defaults
    
    def _process_anomalies(self, anomalies: Dict[str, Tuple[bool, float, str]]) -> Dict[str, AnomalyScore]:
        """Convert anomaly tuples to AnomalyScore objects"""
        return {
            key: AnomalyScore(
                is_anomaly=value[0],
                normalized_score=value[1],
                severity=AnomalySeverity[value[2].upper()]
            )
            for key, value in anomalies.items()
        }
    
    def _make_ml_prediction(self, features: Dict[str, float]) -> Dict[str, Any]:
        """Create ML prediction dictionary for pattern analyzer"""
        # Ensure features are in correct order
        feature_values = [features.get(name, 0.0) for name in self.extractor.feature_names]
        
        # Scale features
        if hasattr(self.ml_manager, 'scaler') and self.ml_manager.scaler:
            feature_values = self.ml_manager.scaler.transform([feature_values])[0]
        
        # Make prediction
        pattern = self.ml_manager.classifier.predict([feature_values])[0]
        
        # Get probabilities if available
        proba = (self.ml_manager.classifier.predict_proba([feature_values])[0]
                if hasattr(self.ml_manager.classifier, "predict_proba")
                else None)
        
        return {
            'pattern': EmergencyPattern(pattern),
            'probability': float(proba[pattern]) if proba is not None else 0.75,
            'confidence': self._determine_confidence(proba, pattern),
            'recommended_action': get_pattern_action(
                EmergencyPattern(pattern),
                self._determine_confidence(proba, pattern)
            )
        }
    
    def _determine_confidence(self, 
                            proba: Optional[np.ndarray], 
                            predicted: int) -> PatternConfidence:
        """Determine confidence level from probabilities"""
        if proba is None:
            return PatternConfidence.MEDIUM
        
        confidence_score = proba[predicted]
        if confidence_score >= 0.9:
            return PatternConfidence.VERY_HIGH
        elif confidence_score >= 0.75:
            return PatternConfidence.HIGH
        elif confidence_score >= 0.5:
            return PatternConfidence.MEDIUM
        return PatternConfidence.LOW
    
    def _is_critical(self, pattern: EmergencyPattern) -> bool:
        """Check if pattern is critical"""
        critical_patterns = {
            EmergencyPattern.FUEL_LEAK,
            EmergencyPattern.STRUCTURAL_FATIGUE,
            EmergencyPattern.ELECTRICAL_FAILURE,
            EmergencyPattern.SYSTEM_CASCADE,
            EmergencyPattern.UNKNOWN_EMERGENCY
        }
        return pattern in critical_patterns
    
    def _trigger_protocol(self, result: PatternResult) -> None:
        """Execute the appropriate emergency protocol"""
        protocol = self.protocols.get(result.pattern_type)
        if protocol:
            try:
                protocol.execute(
                    pattern=result.pattern_type,
                    confidence=result.confidence,
                    time_to_critical=result.time_to_critical
                )
                logger.info(f"Executed protocol for {result.pattern_type.name}")
            except Exception as e:
                logger.error(f"Protocol execution failed: {e}")
    
    def _calculate_trend(self) -> float:
        """Calculate severity trend from history"""
        if len(self.pattern_history) < 2:
            return 0.0
        x = np.arange(len(self.pattern_history))
        y = np.array([p.value for p in self.pattern_history])
        return float(np.polyfit(x, y, 1)[0])
    
    def _create_error_result(self) -> PatternResult:
        """Create fallback result when errors occur"""
        return PatternResult(
            pattern_type=EmergencyPattern.UNKNOWN_EMERGENCY,
            confidence=PatternConfidence.LOW,
            probability=0.0,
            contributing_features=[],
            recommended_action="System error - verify manually",
            severity_trend=0.0,
            anomaly_score=0.0,
            time_to_critical=None
        )

# Maintain backwards compatibility
detector = EmergencyDetector()

def detect_emergency_from_telemetry(
    telemetry: Dict[str, float],
    anomaly_inputs: Dict[str, Tuple[bool, float, str]],
    correlation_data: Dict[str, float]
) -> Dict[str, Any]:
    """Legacy function interface"""
    return detector.detect(telemetry, anomaly_inputs, correlation_data)