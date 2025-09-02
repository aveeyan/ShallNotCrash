# shallnotcrash/emergency/analyzers/anomaly_detector.py

#!/usr/bin/env python3
"""
Robust Anomaly Detection for Flight Systems - FIXED VERSION
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import IntEnum, auto
import time
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Realistic baseline values for C172P
C172P_BASELINE = {
    "rpm": {"mean": 2300.0, "std": 100.0},
    "oil_pressure": {"mean": 60.0, "std": 5.0},
    "oil_temp": {"mean": 180.0, "std": 20.0},
    "cht": {"mean": 380.0, "std": 30.0},
    "egt": {"mean": 1350.0, "std": 50.0},
    "fuel_flow": {"mean": 9.5, "std": 1.0},
    "g_load": {"mean": 1.0, "std": 0.2},
    "vibration": {"mean": 0.1, "std": 0.05},
    "bus_volts": {"mean": 28.0, "std": 0.5},
    "control_asymmetry": {"mean": 0.0, "std": 0.1}
}

class FlightPhase(IntEnum):
    UNKNOWN = 0
    TAKEOFF = 1
    CLIMB = 2
    CRUISE = 3
    DESCENT = 4
    LANDING = 5

class AnomalySeverity(IntEnum):
    NORMAL = 0
    ADVISORY = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4

@dataclass
class AnomalyScore:
    parameter: str
    value: float
    baseline: float
    deviation: float
    normalized_score: float
    is_anomaly: bool
    severity: AnomalySeverity
    flight_phase: FlightPhase
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    status_message: str = "Normal operation"

class AnomalyDetector:
    """Simple but effective anomaly detector for real-time use"""
    
    def __init__(self):
        self.baselines = C172P_BASELINE
        self.min_samples = 10
        self.history = {param: [] for param in self.baselines.keys()}
        
        # Parameter-specific thresholds
        self.thresholds = {
            'rpm': 2.5,          # 2.5 sigma for RPM
            'oil_pressure': 3.0, # 3.0 sigma for oil pressure (more sensitive)
            'oil_temp': 2.8,
            'cht': 2.8,
            'egt': 2.8,
            'fuel_flow': 3.0,
            'g_load': 2.0,       # More sensitive to G-load changes
            'vibration': 2.5,
            'bus_volts': 3.0,
            'control_asymmetry': 2.0
        }
    
    def detect(self, telemetry: Dict[str, float], 
               flight_phase: FlightPhase = FlightPhase.CRUISE) -> Dict[str, AnomalyScore]:
        """Detect anomalies in telemetry data"""
        results = {}
        
        for param, value in telemetry.items():
            if param not in self.baselines:
                continue
                
            # Update history
            self.history[param].append(value)
            if len(self.history[param]) > 100:  # Keep reasonable history
                self.history[param] = self.history[param][-100:]
            
            # Get baseline stats
            baseline = self.baselines[param]
            threshold = self.thresholds.get(param, 3.0)
            
            # Calculate z-score
            z_score = abs(value - baseline["mean"]) / max(baseline["std"], 0.01)
            
            # Determine severity
            severity = self._score_to_severity(z_score, threshold)
            is_anomaly = severity != AnomalySeverity.NORMAL
            
            results[param] = AnomalyScore(
                parameter=param,
                value=value,
                baseline=baseline["mean"],
                deviation=baseline["std"],
                normalized_score=z_score,
                is_anomaly=is_anomaly,
                severity=severity,
                flight_phase=flight_phase,
                status_message=self._get_status_message(param, severity, z_score)
            )
        
        return results
    
    def _score_to_severity(self, score: float, threshold: float) -> AnomalySeverity:
        """Convert z-score to severity level"""
        if score > threshold * 2.0:
            return AnomalySeverity.EMERGENCY
        elif score > threshold * 1.5:
            return AnomalySeverity.CRITICAL
        elif score > threshold * 1.2:
            return AnomalySeverity.WARNING
        elif score > threshold:
            return AnomalySeverity.ADVISORY
        else:
            return AnomalySeverity.NORMAL
    
    def _get_status_message(self, param: str, severity: AnomalySeverity, score: float) -> str:
        """Generate appropriate status message"""
        param_name = param.replace('_', ' ').title()
        
        messages = {
            AnomalySeverity.NORMAL: f"{param_name} normal",
            AnomalySeverity.ADVISORY: f"{param_name} slightly abnormal",
            AnomalySeverity.WARNING: f"{param_name} warning - monitor closely",
            AnomalySeverity.CRITICAL: f"{param_name} CRITICAL - take action",
            AnomalySeverity.EMERGENCY: f"{param_name} EMERGENCY - immediate action required"
        }
        
        return messages.get(severity, "Status unknown")
    
    def update_baseline(self, param: str, new_mean: float, new_std: float):
        """Update baseline statistics for a parameter"""
        if param in self.baselines:
            self.baselines[param]["mean"] = new_mean
            self.baselines[param]["std"] = max(new_std, 0.01)

# Singleton instance
ANOMALY_DETECTOR = AnomalyDetector()
