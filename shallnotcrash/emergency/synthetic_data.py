#!/usr/bin/env python3
"""
Synthetic Data Generation for the ShallNotCrash Emergency Module.
CORRECTED VERSION: Generates realistic, overlapping, and balanced data.
"""
import numpy as np
import random
from typing import List, Dict, Any, Optional

from .analyzers.anomaly_detector import AnomalyScore, AnomalySeverity, FlightPhase
from .analyzers.pattern_recognizer import EmergencyPattern

def generate_training_data(
    num_samples: int,
    normal_flight_ratio: float = 0.8, # NEW: Control class balance
    seed: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Generates a realistic dataset with overlapping distributions and proper class balance.
    """
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    data = []
    
    telemetry_keys = [
        'rpm', 'oil_pressure', 'oil_temp', 'cht', 'egt', 'fuel_flow',
        'g_load', 'vibration', 'aileron', 'elevator', 'rudder', 'bus_volts'
    ]

    emergency_params = {
        EmergencyPattern.ENGINE_DEGRADATION: {'rpm', 'oil_pressure', 'vibration', 'egt'},
        EmergencyPattern.FUEL_LEAK: {'fuel_flow'},
        EmergencyPattern.STRUCTURAL_FATIGUE: {'g_load', 'vibration'},
        EmergencyPattern.ELECTRICAL_FAILURE: {'bus_volts'},
        EmergencyPattern.SYSTEM_CASCADE: {'rpm', 'bus_volts', 'fuel_flow'},
        EmergencyPattern.WEATHER_DISTRESS: {'vibration', 'g_load'}, # Added for completeness
        EmergencyPattern.UNKNOWN_EMERGENCY: set()
    }
    
    emergency_patterns = [p for p in EmergencyPattern if p != EmergencyPattern.NORMAL]

    for _ in range(num_samples):
        # CORRECTED: Generate a realistic ratio of normal vs. emergency flights
        is_normal_flight = random.random() < normal_flight_ratio
        
        pattern_label = EmergencyPattern.NORMAL if is_normal_flight else random.choice(emergency_patterns)
        
        telemetry = {key: np.random.normal(1000, 200) for key in telemetry_keys}
        anomaly_scores: Dict[str, AnomalyScore] = {}

        # --- Generate Realistic Telemetry and Scores ---
        active_emergency_params = emergency_params.get(pattern_label, set())

        # Modify telemetry for the active emergency
        if pattern_label == EmergencyPattern.ENGINE_DEGRADATION:
            telemetry['rpm'], telemetry['oil_pressure'] = np.random.normal(500, 50), np.random.normal(15, 5)
        elif pattern_label == EmergencyPattern.FUEL_LEAK:
            telemetry['fuel_flow'] = np.random.normal(0.5, 0.1)
        elif pattern_label == EmergencyPattern.ELECTRICAL_FAILURE:
            telemetry['bus_volts'] = np.random.normal(22, 1)

        for key in telemetry_keys:
            # CORRECTED: Create overlapping score distributions for realism
            if key in active_emergency_params:
                # High scores for parameters related to the active emergency
                score = np.random.normal(loc=3.5, scale=1.0)
            elif is_normal_flight and random.random() < 0.1:
                # For normal flights, occasionally introduce a small, random anomaly
                score = np.random.normal(loc=1.8, scale=0.4)
            else:
                # Baseline low scores for unaffected parameters
                score = np.random.gamma(shape=1.0, scale=0.5)

            score = max(0, score) # Ensure score is not negative

            # Map the score to the 5-level severity
            if score > 4.0: severity = AnomalySeverity.EMERGENCY
            elif score > 3.0: severity = AnomalySeverity.CRITICAL
            elif score > 2.4: severity = AnomalySeverity.WARNING
            elif score > 1.8: severity = AnomalySeverity.ADVISORY
            else: severity = AnomalySeverity.NORMAL
            
            is_anomaly = severity != AnomalySeverity.NORMAL

            anomaly_scores[key] = AnomalyScore(
                parameter=key, value=telemetry[key], baseline=1000, deviation=0,
                normalized_score=score, is_anomaly=is_anomaly, severity=severity,
                flight_phase=FlightPhase.CRUISE
            )

        sample = {
            'telemetry': telemetry,
            'anomaly_scores': anomaly_scores,
            'pattern_label': pattern_label.value
        }
        data.append(sample)

    return data
