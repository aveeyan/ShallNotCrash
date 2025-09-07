# shallnotcrash/emergency/analyzers/anomaly_detector.py
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass, field
from enum import IntEnum
import time
import logging

logger = logging.getLogger(__name__)

# [MODIFIED] Added baselines for new aerodynamic features
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
    "control_asymmetry": {"mean": 0.0, "std": 0.1},
    "airspeed": {"mean": 110.0, "std": 20.0},
    "yaw_rate": {"mean": 0.0, "std": 5.0},
    "roll": {"mean": 0.0, "std": 10.0},
    "pitch": {"mean": 0.0, "std": 5.0},
}

class FlightPhase(IntEnum):
    UNKNOWN = 0; TAKEOFF = 1; CLIMB = 2; CRUISE = 3; DESCENT = 4; LANDING = 5

class AnomalySeverity(IntEnum):
    NORMAL = 0; ADVISORY = 1; WARNING = 2; CRITICAL = 3; EMERGENCY = 4

@dataclass
class AnomalyScore:
    parameter: str; value: float; baseline: float; deviation: float
    normalized_score: float; is_anomaly: bool; severity: AnomalySeverity
    flight_phase: FlightPhase; timestamp: float = field(default_factory=time.time)

class AnomalyDetector:
    """
    [UPGRADED] Anomaly detector that now considers both absolute values (z-score)
    and the rate of change (derivative) to detect anomalies.
    """
    
    def __init__(self):
        self.baselines = C172P_BASELINE
        # [NEW] Add memory for the previous telemetry state to calculate rate of change.
        self.previous_telemetry: Optional[Dict[str, float]] = None
        self.last_timestamp: Optional[float] = None
        
        self.thresholds = {
            'rpm': 2.5, 'oil_pressure': 3.0, 'oil_temp': 2.8, 'cht': 2.8,
            'egt': 2.8, 'fuel_flow': 3.0, 'g_load': 2.0, 'vibration': 2.5,
            'bus_volts': 3.0, 'control_asymmetry': 2.0, 'airspeed': 2.5,
            'yaw_rate': 2.0, 'roll': 2.0, 'pitch': 2.0
        }
        # [NEW] Thresholds for how fast a value can change per second before it's anomalous.
        self.change_rate_thresholds = {
            'rpm': 500, 'oil_pressure': 20, 'g_load': 1.5, 'airspeed': 30,
            'yaw_rate': 45, 'roll': 45, 'pitch': 30, 'fuel_flow': 5.0
        }
    
    def detect(self, telemetry: Dict[str, float], 
               flight_phase: FlightPhase = FlightPhase.CRUISE) -> Dict[str, AnomalyScore]:
        results = {}
        current_timestamp = time.time()
        
        for param, value in telemetry.items():
            if param not in self.baselines:
                continue
            
            baseline = self.baselines[param]
            threshold = self.thresholds.get(param, 3.0)
            
            # --- Score 1: Deviation from static baseline (Z-score) ---
            z_score = abs(value - baseline["mean"]) / max(baseline["std"], 0.01)
            
            # --- [NEW] Score 2: Rate of Change ---
            change_score = 0.0
            if self.previous_telemetry and self.last_timestamp and param in self.change_rate_thresholds:
                delta_t = current_timestamp - self.last_timestamp
                if delta_t > 1e-6: # Avoid division by zero
                    rate_of_change = abs(value - self.previous_telemetry.get(param, value)) / delta_t
                    # Score is how many times the rate of change exceeds its threshold
                    change_score = rate_of_change / self.change_rate_thresholds[param]
            
            # [MODIFIED] The final score is the HIGHER of the two scores.
            # This means either a steady out-of-bounds value OR a sudden,
            # rapid change can trigger an anomaly.
            final_score = max(z_score, change_score)
            
            severity = self._score_to_severity(final_score, threshold)
            
            results[param] = AnomalyScore(
                parameter=param, value=value, baseline=baseline["mean"],
                deviation=baseline["std"], normalized_score=final_score,
                is_anomaly=(severity != AnomalySeverity.NORMAL), severity=severity,
                flight_phase=flight_phase
            )

        # [NEW] Update memory for the next cycle
        self.previous_telemetry = telemetry
        self.last_timestamp = current_timestamp
        
        return results
    
    def _score_to_severity(self, score: float, threshold: float) -> AnomalySeverity:
        if score > threshold * 2.0: return AnomalySeverity.EMERGENCY
        elif score > threshold * 1.5: return AnomalySeverity.CRITICAL
        elif score > threshold * 1.2: return AnomalySeverity.WARNING
        elif score > threshold: return AnomalySeverity.ADVISORY
        else: return AnomalySeverity.NORMAL

# [FIX] The global singleton instance has been removed to prevent state corruption.
# The telemetry_worker in flightgear.py will now create its own private instance.