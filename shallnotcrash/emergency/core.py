#!/usr/bin/env python3
"""
Core System Coordinator for the ShallNotCrash Emergency Module
"""
import logging
from typing import Dict, Any
from dataclasses import asdict

from .analyzers.anomaly_detector import FlightPhase, AnomalyScore
from .analyzers.correlation_analyzer import CORRELATION_ANALYZER, CorrelationDiagnostic
from .analyzers.pattern_recognizer import PATTERN_RECOGNIZER, PatternResult, EmergencyPattern

logger = logging.getLogger(__name__)

# Parameter groupings are essential for the coordinator's logic
ENGINE_PARAMS = {'rpm', 'oil_pressure', 'cht', 'egt', 'oil_temp', 'vibration'}
FUEL_PARAMS = {'fuel_flow'}
STRUCTURAL_PARAMS = {'g_load', 'aileron', 'elevator', 'rudder', 'vibration'}

class EmergencyCoordinator:
    """An orchestrator that correctly sequences the analysis pipeline."""
    def __init__(self):
        self.correlation_analyzer = CORRELATION_ANALYZER
        self.pattern_recognizer = PATTERN_RECOGNIZER
        logger.info("Emergency Coordinator initialized.")
        self.is_loaded = True

    def detect(self, telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], flight_phase: FlightPhase = FlightPhase.CRUISE) -> PatternResult:
        """
        Executes the full, integrated analysis pipeline using provided anomaly scores.
        This is the architecturally sound method that prevents data corruption.
        
        Args:
            telemetry: The raw telemetry data.
            anomaly_scores: The pre-computed anomaly scores for this telemetry sample.
            flight_phase: The current phase of flight.
        """
        try:
            # The coordinator ACCEPTS anomaly scores as ground truth. It does not generate them.
            
            # --- Step 1: Correlation Analysis ---
            self.correlation_analyzer.update_systems(
                engine_status={k: v for k, v in anomaly_scores.items() if k in ENGINE_PARAMS},
                fuel_status={k: v for k, v in anomaly_scores.items() if k in FUEL_PARAMS},
                structural_status={k: v for k, v in anomaly_scores.items() if k in STRUCTURAL_PARAMS}
            )
            correlation_data: CorrelationDiagnostic = self.correlation_analyzer.analyze()

            # --- Step 2: Pattern Recognition ---
            final_result: PatternResult = self.pattern_recognizer.predict_pattern(
                telemetry=telemetry,
                anomaly_scores=anomaly_scores,
                correlation_data=correlation_data.correlated_systems
            )
            
            return final_result

        except Exception as e:
            logger.error(f"Catastrophic failure in detection pipeline: {e}", exc_info=True)
            return PatternResult(pattern_type=EmergencyPattern.UNKNOWN_EMERGENCY, confidence=0, probability=0.0, contributing_features=["Pipeline Exception"])

# --- Public Interface ---
EMERGENCY_COORDINATOR = EmergencyCoordinator()

def detect_emergency(telemetry: Dict[str, float], anomaly_scores: Dict[str, Any], flight_phase: FlightPhase = FlightPhase.CRUISE) -> Dict[str, Any]:
    """Public-facing function for the entire emergency detection pipeline."""
    result_dataclass = EMERGENCY_COORDINATOR.detect(telemetry, anomaly_scores, flight_phase)
    return asdict(result_dataclass)
