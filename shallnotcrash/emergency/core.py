#!/usr/bin/env python3
"""
Core Emergency Detection Coordinator

This module serves as the central pipeline for emergency detection. It coordinates the
flow of data between the specialized analyzer modules, ensuring a clear and sequential
process from raw telemetry to a final, actionable diagnosis.
"""
import logging
from typing import Dict, Any
from dataclasses import asdict

# Import the self-contained analyzer singletons
from .analyzers.anomaly_detector import ANOMALY_DETECTOR, FlightPhase
from .analyzers.correlation_analyzer import CORRELATION_ANALYZER
from .analyzers.pattern_recognizer import (
    PATTERN_RECOGNIZER, 
    PatternResult, 
    EmergencyPattern, 
    PatternConfidence
)

logger = logging.getLogger(__name__)

# Define which parameters belong to which aircraft system.
# This allows us to sort the anomaly data for the correlation analyzer.
ENGINE_PARAMS = {'rpm', 'oil_pressure', 'cht', 'egt', 'oil_temp', 'vibration'}
FUEL_PARAMS = {'fuel_flow'}
STRUCTURAL_PARAMS = {'g_load', 'aileron', 'elevator', 'rudder'}


class EmergencyCoordinator:
    """
    A simple coordinator that pipes data through the analytical components.
    Its sole responsibility is to manage the detection workflow.
    """
    def __init__(self, model_path: str = "models/c172p_emergency_model.joblib"):
        """Initializes the coordinator and its underlying analyzers."""
        self.anomaly_detector = ANOMALY_DETECTOR
        self.correlation_analyzer = CORRELATION_ANALYZER
        self.pattern_recognizer = PATTERN_RECOGNIZER
        
        try:
            self.pattern_recognizer.load_models(model_path)
            logger.info(f"Successfully loaded emergency detection model from {model_path}")
        except Exception as e:
            logger.warning(f"Could not load ML model from {model_path}: {e}. Pattern recognizer may use fallback rules.")

    def detect(self, telemetry: Dict[str, float], flight_phase: FlightPhase = FlightPhase.CRUISE) -> PatternResult:
        """Executes the full, sequential emergency detection pipeline."""
        try:
            # --- Step 1: Detect low-level statistical anomalies ---
            # The pipeline now starts here. The old protocols are fully removed.
            anomaly_scores = self.anomaly_detector.detect(telemetry, flight_phase)

            # --- Step 2: Analyze cross-system correlations ---
            
            # 2a. Filter the anomaly scores into system-specific dictionaries.
            engine_anomalies = {k: v for k, v in anomaly_scores.items() if k in ENGINE_PARAMS}
            fuel_anomalies = {k: v for k, v in anomaly_scores.items() if k in FUEL_PARAMS}
            structural_anomalies = {k: v for k, v in anomaly_scores.items() if k in STRUCTURAL_PARAMS}

            # 2b. Update the analyzer with the correctly formatted data.
            self.correlation_analyzer.update_systems(
                engine_status=engine_anomalies,
                fuel_status=fuel_anomalies,
                structural_status=structural_anomalies
            )
            
            # 2c. Perform the analysis.
            correlation_result = self.correlation_analyzer.analyze()

            # --- Step 3: Recognize high-level emergency patterns using ML ---
            final_pattern = self.pattern_recognizer.predict_pattern(
                telemetry=telemetry,
                anomaly_scores=anomaly_scores,
                correlation_data=correlation_result.correlated_systems
            )
            
            return final_pattern

        except Exception as e:
            logger.error(f"Critical error in detection pipeline: {e}", exc_info=True)
            return PatternResult(
                pattern_type=EmergencyPattern.UNKNOWN_EMERGENCY,
                confidence=PatternConfidence.LOW,
                probability=0.0,
                contributing_features=["detection_pipeline_error"],
                recommended_action="System error - verify manually"
            )

# --- Public Interface ---
EMERGENCY_COORDINATOR = EmergencyCoordinator()

def detect_emergency(telemetry: Dict[str, float], flight_phase: FlightPhase = FlightPhase.CRUISE) -> Dict[str, Any]:
    """Public-facing function for the entire emergency detection pipeline."""
    result_dataclass = EMERGENCY_COORDINATOR.detect(telemetry, flight_phase)
    return asdict(result_dataclass)
