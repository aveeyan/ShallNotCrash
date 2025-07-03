#!/usr/bin/env python3
"""
Anomaly Detection for Flight Systems
Provides statistical monitoring using adaptive thresholds
"""
import numpy as np
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class AnomalyScore:
    """Anomaly detection result with flight context"""
    parameter: str
    value: float
    mean: float
    std_dev: float
    z_score: float
    is_anomaly: bool
    flight_phase: str = "CRUISE"  # Default phase

class AnomalyDetector:
    """Adaptive statistical monitoring with flight-phase awareness"""
    ANOMALY_THRESHOLD = 3.0  # 3 standard deviations
    FLIGHT_PHASES = ["TAKEOFF", "CLIMB", "CRUISE", "DESCENT", "LANDING"]
    
    def __init__(self):
        self.parameter_stats = {}
        self.phase_models = {phase: {} for phase in self.FLIGHT_PHASES}
        
    def train(self, training_data: Dict[str, Dict[str, List[float]]]):
        """Train models for each flight phase"""
        for phase, params in training_data.items():
            for param, values in params.items():
                if len(values) > 1:
                    mean = np.mean(values)
                    std = np.std(values)
                    self.phase_models[phase][param] = (mean, std)
    
    def detect(self, telemetry: Dict[str, float], flight_phase: str) -> Dict[str, AnomalyScore]:
        """Detect anomalies with flight phase context"""
        results = {}
        model = self.phase_models.get(flight_phase, {})
        
        for param, value in telemetry.items():
            if param in model:
                mean, std = model[param]
                if std == 0:
                    z_score = 0
                else:
                    z_score = abs(value - mean) / std
                
                results[param] = AnomalyScore(
                    parameter=param,
                    value=value,
                    mean=mean,
                    std_dev=std,
                    z_score=z_score,
                    is_anomaly=z_score > self.ANOMALY_THRESHOLD,
                    flight_phase=flight_phase
                )
        return results

# Singleton instance
ANOMALY_DETECTOR = AnomalyDetector()

def detect_anomalies(telemetry: Dict[str, float], flight_phase: str) -> Dict[str, AnomalyScore]:
    """Detect phase-aware anomalies"""
    return ANOMALY_DETECTOR.detect(telemetry, flight_phase)