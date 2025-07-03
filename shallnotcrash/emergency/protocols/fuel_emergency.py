#!/usr/bin/env python3
"""
Cessna 172P Fuel Emergency Detection
Provides conservative diagnostics of fuel system health
"""
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Tuple

# Corrected imports based on project structure
from ...airplane.constants import C172PConstants
from ..constants import FuelThresholds

class FuelEmergencySeverity(IntEnum):
    NORMAL = 0
    ADVISORY = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4

@dataclass
class FuelDiagnostic:
    is_emergency: bool
    severity: FuelEmergencySeverity
    confidence: float
    diagnostics: Dict[str, dict]
    failed_components: List[str]

class FuelEmergencyDetector:
    """Conservative fuel system health monitoring"""
    # Parameter importance weights
    PARAM_WEIGHTS = {
        'total_fuel': 0.40,
        'fuel_flow': 0.35,
        'imbalance': 0.25
    }
    
    def __init__(self):
        self.thresholds = self._initialize_thresholds()

    def _initialize_thresholds(self) -> Dict[str, Dict]:
        """Initialize thresholds with operational buffers"""
        return {
            'imbalance': {
                'normal': (0, FuelThresholds.IMBALANCE['WARNING'] * 1.1),
                'critical': FuelThresholds.IMBALANCE['CRITICAL']
            },
            'total_fuel': {
                'normal': (FuelThresholds.QTY['WARNING'] * 0.9, 
                          C172PConstants.FUEL['TOTAL_CAPACITY_GAL']),
                'critical': FuelThresholds.QTY['CRITICAL'] * 0.8
            },
            'fuel_flow': {
                'normal': (FuelThresholds.STARVATION['FLOW_CRITICAL'] * 1.2, 
                          C172PConstants.ENGINE['MAX_FUEL_FLOW']),
                'critical': FuelThresholds.STARVATION['FLOW_CRITICAL'] * 1.1
            }
        }

    def detect(self, telemetry: Dict[str, float]) -> FuelDiagnostic:
        """Detect fuel emergency with conservative diagnostics"""
        diagnostics = {}
        failed_components = []
        confidence = 0.0
        max_severity = FuelEmergencySeverity.NORMAL
        
        # Calculate derived parameters
        telemetry['imbalance'] = abs(telemetry.get('fuel_left', 0) - 
                                  telemetry.get('fuel_right', 0))
        telemetry['total_fuel'] = telemetry.get('fuel_left', 0) + telemetry.get('fuel_right', 0)
        
        # Calculate endurance
        fuel_flow = telemetry.get('fuel_flow', C172PConstants.ENGINE['MIN_FUEL_FLOW_IDLE'])
        telemetry['endurance'] = (telemetry['total_fuel'] / fuel_flow * 60 
                                 if fuel_flow > 0 else 0)
        
        # Check each parameter
        for param, thresholds in self.thresholds.items():
            value = telemetry.get(param, None)
            status = self._check_parameter(param, value, thresholds)
            diagnostics[param] = status
            
            # Only consider WARNING or higher for confidence
            if status['severity'] >= FuelEmergencySeverity.WARNING:
                severity_value = status['severity'].value
                severity_factor = (severity_value - 1)  # 1 for WARNING, 2 for CRITICAL, 3 for EMERGENCY
                confidence += self.PARAM_WEIGHTS.get(param, 0.1) * severity_factor
                
                if status['severity'] >= FuelEmergencySeverity.CRITICAL:
                    failed_components.append(param)
                
                if status['severity'] > max_severity:
                    max_severity = status['severity']
        
        # Determine emergency state conservatively
        is_emergency = max_severity >= FuelEmergencySeverity.CRITICAL
        confidence = min(1.0, confidence)
        
        return FuelDiagnostic(
            is_emergency=is_emergency,
            severity=max_severity,
            confidence=confidence,
            diagnostics=diagnostics,
            failed_components=failed_components
        )

    def _check_parameter(self, param: str, value: Optional[float], 
                        thresholds: dict) -> dict:
        """Evaluate parameters with conservative thresholds"""
        if value is None:
            return {
                'value': None,
                'status': 'NO_DATA',
                'severity': FuelEmergencySeverity.ADVISORY,
                'message': 'Fuel sensor data unavailable',
                'normal_range': thresholds.get('normal'),
                'critical_threshold': thresholds.get('critical')
            }
            
        # Extract thresholds
        normal_range = thresholds.get('normal', (0, 1000))
        critical_threshold = thresholds.get('critical', 0)
        
        # Determine condition type
        if param in ['total_fuel', 'fuel_flow']:  # Low is critical
            critical = value <= critical_threshold
            in_range = normal_range[0] <= value <= normal_range[1]
        else:  # High is critical (imbalance)
            critical = value >= critical_threshold
            in_range = normal_range[0] <= value <= normal_range[1]
        
        # Create status conservatively
        if critical:
            status = 'CRITICAL'
            severity = FuelEmergencySeverity.EMERGENCY
            message = f"{param.replace('_', ' ').title()} critical: {value:.1f}"
        elif not in_range:
            status = 'WARNING'
            severity = FuelEmergencySeverity.WARNING
            low, high = normal_range
            message = (f"{param.replace('_', ' ').title()} out of range: {value:.1f} "
                      f"(Acceptable: {low:.1f}-{high:.1f})")
        else:
            status = 'NORMAL'
            severity = FuelEmergencySeverity.NORMAL
            message = f"{param.replace('_', ' ').title()} normal"
        
        return {
            'value': value,
            'status': status,
            'severity': severity,
            'message': message,
            'normal_range': thresholds.get('normal'),
            'critical_threshold': thresholds.get('critical')
        }

# Singleton instance
FUEL_EMERGENCY_DETECTOR = FuelEmergencyDetector()

def detect_fuel_emergency(telemetry: Dict[str, float]) -> FuelDiagnostic:
    """Detect fuel emergency with conservative diagnostics"""
    return FUEL_EMERGENCY_DETECTOR.detect(telemetry)
