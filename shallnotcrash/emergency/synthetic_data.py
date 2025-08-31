# shallnotcrash/emergency/synthetic_data.py
"""
[V3 - REALISM & RANDOMNESS]
This version improves the data generator by adding three key features for
more robust model training: realistic sensor noise, overlapping emergency
signatures, and variable event severity.
"""
import numpy as np
import random
from typing import List, Dict, Any, Optional

from .analyzers.anomaly_detector import AnomalyScore, AnomalySeverity, FlightPhase
from .analyzers.pattern_recognizer import EmergencyPattern

# [NEW] 1. Add Realistic Sensor Noise
# Define how "noisy" each sensor is. Vibration is very noisy, volts are stable.
NOISE_LEVELS = {
    'rpm': 10, 'oil_pressure': 2, 'oil_temp': 1.5, 'cht': 5, 'egt': 10,
    'fuel_flow': 0.1, 'g_load': 0.05, 'vibration': 0.08, 'control_asymmetry': 0.1, 'bus_volts': 0.25
}

def generate_training_data(
    num_samples: int,
    normal_flight_ratio: float = 0.8,
    seed: Optional[int] = None
) -> List[Dict[str, Any]]:
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    data = []
    telemetry_keys = list(NOISE_LEVELS.keys())
    
    emergency_params = {
        EmergencyPattern.ENGINE_DEGRADATION: {'rpm', 'oil_pressure', 'vibration'},
        EmergencyPattern.FUEL_LEAK: {'fuel_flow'},
        EmergencyPattern.STRUCTURAL_FATIGUE: {'vibration', 'control_asymmetry'},
        EmergencyPattern.ELECTRICAL_FAILURE: {'bus_volts'},
        EmergencyPattern.SYSTEM_CASCADE: {'rpm', 'bus_volts', 'fuel_flow'},
        EmergencyPattern.WEATHER_DISTRESS: {'vibration', 'g_load'},
        EmergencyPattern.UNKNOWN_EMERGENCY: set()
    }
    
    all_possible_params = {p for params in emergency_params.values() for p in params}
    emergency_patterns = [p for p in EmergencyPattern if p != EmergencyPattern.NORMAL]

    for _ in range(num_samples):
        is_normal_flight = random.random() < normal_flight_ratio
        pattern_label = EmergencyPattern.NORMAL if is_normal_flight else random.choice(emergency_patterns)
        
        # Start with a baseline of normal telemetry
        telemetry = {
            'rpm': 2300, 'oil_pressure': 50, 'oil_temp': 200, 'cht': 400, 'egt': 1300,
            'fuel_flow': 10, 'g_load': 1.0, 'vibration': 0.1, 'control_asymmetry': 0, 'bus_volts': 24.5
        }
        
        active_emergency_params = emergency_params.get(pattern_label, set())

        # --- [NEW] 2. & 3. Overlapping Signatures and Variable Severity ---
        if not is_normal_flight:
            severity_multiplier = random.uniform(0.7, 1.3) # Randomize how bad the failure is
            if pattern_label == EmergencyPattern.ENGINE_DEGRADATION:
                telemetry['rpm'] -= 1500 * severity_multiplier
                telemetry['oil_pressure'] -= 35 * severity_multiplier
                telemetry['vibration'] += 0.5 * severity_multiplier
                if random.random() < 0.2: # 20% chance of a secondary effect
                    telemetry['bus_volts'] -= 1.5
            elif pattern_label == EmergencyPattern.FUEL_LEAK:
                telemetry['fuel_flow'] -= 8 * severity_multiplier
                if random.random() < 0.3: # 30% chance fuel issue affects engine RPM
                    telemetry['rpm'] -= 200 * severity_multiplier
            # ... (Add similar logic for other emergencies) ...
            
        # --- [NEW] Apply realistic noise to ALL parameters ---
        for key, base_value in telemetry.items():
            noise = np.random.normal(0, NOISE_LEVELS.get(key, 0.1))
            telemetry[key] = base_value + noise
            
        # --- (Anomaly score generation remains the same) ---
        anomaly_scores: Dict[str, AnomalyScore] = {}
        # ... (This part of the code is unchanged) ...
        for key in telemetry_keys:
            if key in active_emergency_params: score = np.random.normal(loc=3.5, scale=1.0)
            elif is_normal_flight and random.random() < 0.1: score = np.random.normal(loc=1.8, scale=0.4)
            else: score = np.random.gamma(shape=1.0, scale=0.5)
            score = max(0, score)
            if score > 4.0: severity = AnomalySeverity.EMERGENCY
            elif score > 3.0: severity = AnomalySeverity.CRITICAL
            elif score > 2.4: severity = AnomalySeverity.WARNING
            elif score > 1.8: severity = AnomalySeverity.ADVISORY
            else: severity = AnomalySeverity.NORMAL
            anomaly_scores[key] = AnomalyScore(parameter=key, value=telemetry[key], baseline=1000, deviation=0,
                                               normalized_score=score, is_anomaly=(severity != AnomalySeverity.NORMAL),
                                               severity=severity, flight_phase=FlightPhase.CRUISE)
        
        sample = {'telemetry': telemetry, 'anomaly_scores': anomaly_scores, 'pattern_label': pattern_label.value}
        data.append(sample)
    return data
