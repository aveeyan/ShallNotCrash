#!/usr/bin/env python3
"""
Advanced Engine Failure Detection for Cessna 172P
Provides detailed diagnostic information about engine health
"""
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

# Relative imports within shallnotcrash package
from ...airplane.constants import EngineThresholds
from ..constants import EmergencySeverity

class EngineFailureSeverity(Enum):
    NORMAL = 0
    ADVISORY = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4

@dataclass
class EngineDiagnostic:
    """Detailed engine health diagnosis"""
    is_failure: bool
    severity: EngineFailureSeverity
    confidence: float
    diagnostics: Dict[str, dict]
    failed_components: List[str]

class EngineFailureDetector:
    """Constants-based engine failure detection with diagnostic details"""
    def __init__(self):
        # Initialize thresholds from constants
        self.thresholds = {
            'rpm': {
                'normal': (EngineThresholds.RPM_MIN, EngineThresholds.RPM_MAX),
                'critical': EngineThresholds.ENGINE_FAILURE_RPM
            },
            'oil_pressure': {
                'normal': (EngineThresholds.OIL_PRESS_MIN, EngineThresholds.OIL_PRESS_MAX),
                'critical': EngineThresholds.OIL_PRESS_CRITICAL
            },
            'cht': {
                'normal': (EngineThresholds.CHT['MIN'], EngineThresholds.CHT['MAX']),
                'critical': EngineThresholds.CHT['CRITICAL']
            },
            'egt': {
                'normal': (EngineThresholds.EGT_MIN, EngineThresholds.EGT_MAX),
                'critical': EngineThresholds.EGT_CRITICAL
            },
            'oil_temp': {
                'normal': (EngineThresholds.OIL_TEMP_MIN, EngineThresholds.OIL_TEMP_MAX),
                'critical': EngineThresholds.OIL_TEMP_CRITICAL
            },
            'vibration': {
                'normal': (0, EngineThresholds.VIBRATION['WARNING']),
                'critical': EngineThresholds.VIBRATION['CRITICAL']
            },
            'fuel_flow': {
                'normal': (EngineThresholds.FUEL_FLOW['MIN_IDLE'], EngineThresholds.FUEL_FLOW['MAX_NORMAL']),
                'critical': EngineThresholds.FUEL_FLOW['MIN_IDLE'] * 0.8
            }
        }

    def detect(self, telemetry: Dict[str, float]) -> EngineDiagnostic:
        """Detect engine failure with detailed diagnostics"""
        diagnostics = {}
        failed_components = []
        confidence = 0.0
        max_severity = EngineFailureSeverity.NORMAL

        # Check each engine parameter
        for param, thresholds in self.thresholds.items():
            value = telemetry.get(param, None)
            status = self._check_parameter(param, value, thresholds)
            diagnostics[param] = status
            
            if status['severity'] != EngineFailureSeverity.NORMAL:
                # Calculate contribution to confidence
                severity_weight = status['severity'].value
                confidence += min(1.0, severity_weight * 0.4)
                
                # Track failed components
                if status['severity'] in [EngineFailureSeverity.CRITICAL, EngineFailureSeverity.EMERGENCY]:
                    failed_components.append(param)
                
                # Track max severity
                if status['severity'].value > max_severity.value:
                    max_severity = status['severity']
        
        # Determine overall failure state
        is_failure = confidence > 0.5
        severity = max_severity
        
        return EngineDiagnostic(
            is_failure=is_failure,
            severity=severity,
            confidence=min(1.0, confidence),
            diagnostics=diagnostics,
            failed_components=failed_components
        )

    def _check_parameter(self, param: str, value: float, thresholds: dict) -> dict:
        """Evaluate a single engine parameter using constant-based thresholds"""
        if value is None:
            return {
                'value': None,
                'status': 'NO_DATA',
                'severity': EngineFailureSeverity.ADVISORY,
                'message': 'Sensor data unavailable'
            }
        
        # Get threshold values
        normal_range = thresholds.get('normal', (0, 1000))
        critical_threshold = thresholds.get('critical', 0)

        # Determine if value is critical
        if 'critical' in thresholds:
            # For parameters where low is critical (rpm, oil_pressure, fuel_flow)
            if param in ['rpm', 'oil_pressure', 'fuel_flow']:
                critical = value < critical_threshold
            # For parameters where high is critical (others)
            else:
                critical = value > critical_threshold
        else:
            critical = False

        # Determine if value is within normal range
        if 'normal' in thresholds:
            low, high = normal_range
            in_range = low <= value <= high
        else:
            in_range = True

        # Create status
        if critical:
            status = 'CRITICAL'
            severity = EngineFailureSeverity.EMERGENCY
            message = (f"{param.upper()} in emergency range: {value} "
                      f"(Threshold: {critical_threshold})")
        elif not in_range:
            status = 'WARNING'
            severity = EngineFailureSeverity.WARNING
            message = (f"{param.upper()} out of normal range: {value} "
                      f"(Normal: {normal_range})")
        else:
            status = 'NORMAL'
            severity = EngineFailureSeverity.NORMAL
            message = f"{param.upper()} within normal parameters"
        
        return {
            'value': value,
            'status': status,
            'severity': severity,
            'message': message,
            'normal_range': thresholds.get('normal'),
            'critical_threshold': thresholds.get('critical')
        }

# Singleton instance
ENGINE_FAILURE_DETECTOR = EngineFailureDetector()

def detect_engine_failure(telemetry: Dict[str, float]) -> EngineDiagnostic:
    """Detect engine failure with detailed diagnostics"""
    return ENGINE_FAILURE_DETECTOR.detect(telemetry)