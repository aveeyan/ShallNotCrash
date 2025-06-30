#!/usr/bin/env python3
"""
Cessna 172P Fuel Emergency Detection
Provides detailed diagnostics of fuel system health using only constants
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Any

# Corrected imports based on project structure
from ...airplane.constants import C172PConstants
from ..constants import FuelThresholds, EmergencySeverity

class FuelEmergencySeverity(Enum):
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
    """Comprehensive fuel system health monitoring using constants only"""
    def __init__(self):
        # Initialize with all values from constants
        self.thresholds = {
            'imbalance': {
                'warning': FuelThresholds.IMBALANCE['WARNING'],
                'critical': FuelThresholds.IMBALANCE['CRITICAL']
            },
            'total_fuel': {
                'warning': FuelThresholds.QTY['WARNING'],
                'critical': FuelThresholds.QTY['CRITICAL']
            },
            'fuel_flow': {
                'starvation': FuelThresholds.STARVATION['FLOW_WARNING']
            }
        }

    def detect(self, telemetry: Dict[str, float]) -> FuelDiagnostic:
        """Detect fuel emergency with detailed diagnostics"""
        diagnostics = {}
        failed_components = []
        confidence = 0.0
        max_severity = FuelEmergencySeverity.NORMAL
        
        # Calculate derived parameters using constants
        telemetry['imbalance'] = abs(telemetry.get('fuel_left', 0) - 
                                  telemetry.get('fuel_right', 0))
        telemetry['total_fuel'] = (telemetry.get('fuel_left', 0) + 
                                  telemetry.get('fuel_right', 0))
        
        # Calculate endurance using constants
        fuel_flow = telemetry.get('fuel_flow', C172PConstants.ENGINE['MIN_FUEL_FLOW_IDLE'])
        telemetry['endurance'] = (telemetry['total_fuel'] / fuel_flow * 60 
                                 if fuel_flow > 0 else 0)
        
        # Check each parameter using constant-based thresholds
        for param, thresholds in self.thresholds.items():
            status = self._check_parameter(param, telemetry.get(param, 0), thresholds)
            diagnostics[param] = status
            
            if status['severity'] != FuelEmergencySeverity.NORMAL:
                # Calculate contribution to confidence
                severity_weight = status['severity'].value
                confidence += min(1.0, severity_weight * 0.4)
                
                # Track failed components
                failed_components.append(param)
                
                # Track max severity
                if status['severity'].value > max_severity.value:
                    max_severity = status['severity']
        
        # Determine overall emergency state
        is_emergency = confidence > 0.6
        
        return FuelDiagnostic(
            is_emergency=is_emergency,
            severity=max_severity,
            confidence=min(1.0, confidence),
            diagnostics=diagnostics,
            failed_components=failed_components
        )

    def _check_parameter(self, param: str, value: float, thresholds: dict) -> dict:
        """Evaluate fuel system parameters using constant-based thresholds"""
        param_status = {
            'value': value,
            'status': 'NORMAL',
            'severity': FuelEmergencySeverity.NORMAL,
            'message': f"{param.replace('_', ' ').title()} within normal parameters",
            'thresholds': thresholds
        }
        
        # Check imbalance against constants
        if param == 'imbalance':
            if 'critical' in thresholds and value > thresholds['critical']:
                param_status.update({
                    'status': 'CRITICAL',
                    'severity': FuelEmergencySeverity.EMERGENCY,
                    'message': (f"Fuel imbalance critical: {value:.1f} gal (max allowed "
                               f"{thresholds['critical']} gal)")
                })
            elif 'warning' in thresholds and value > thresholds['warning']:
                param_status.update({
                    'status': 'WARNING',
                    'severity': FuelEmergencySeverity.WARNING,
                    'message': (f"Fuel imbalance warning: {value:.1f} gal (max normal "
                               f"{thresholds['warning']} gal)")
                })
        
        # Check total fuel against constants
        elif param == 'total_fuel':
            if 'critical' in thresholds and value < thresholds['critical']:
                param_status.update({
                    'status': 'CRITICAL',
                    'severity': FuelEmergencySeverity.EMERGENCY,
                    'message': (f"Total fuel critical: {value:.1f} gal (min safe "
                               f"{thresholds['critical']} gal)")
                })
            elif 'warning' in thresholds and value < thresholds['warning']:
                param_status.update({
                    'status': 'WARNING',
                    'severity': FuelEmergencySeverity.WARNING,
                    'message': (f"Total fuel low: {value:.1f} gal (min normal "
                               f"{thresholds['warning']} gal)")
                })
        
        # Check fuel flow against constants
        elif param == 'fuel_flow':
            if 'starvation' in thresholds and value < thresholds['starvation']:
                param_status.update({
                    'status': 'CRITICAL',
                    'severity': FuelEmergencySeverity.CRITICAL,
                    'message': (f"Fuel flow starvation: {value:.1f} GPH (min required "
                               f"{thresholds['starvation']} GPH)")
                })
        
        return param_status

# Singleton instance
FUEL_EMERGENCY_DETECTOR = FuelEmergencyDetector()

def detect_fuel_emergency(telemetry: Dict[str, float]) -> FuelDiagnostic:
    """Detect fuel emergency with detailed diagnostics"""
    return FUEL_EMERGENCY_DETECTOR.detect(telemetry)
