#!/usr/bin/env python3
"""
Structural Failure Detection for Cessna 172P
Identifies structural integrity issues with conservative thresholds
"""
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Optional, Tuple
import math

# Relative imports within shallnotcrash package
from shallnotcrash.emergency.constants import StructuralFailureThresholds

class StructuralFailureSeverity(IntEnum):
    """Structural failure severity levels with integer comparisons"""
    NORMAL = 0
    ADVISORY = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4

@dataclass
class StructuralDiagnostic:
    """Structural integrity diagnosis"""
    is_failure: bool
    severity: StructuralFailureSeverity
    confidence: float
    diagnostics: Dict[str, dict]
    failed_components: List[str]
    status_message: str

class StructuralFailureDetector:
    """Conservative structural failure detection with aviation-grade thresholds"""
    # Parameter importance weights
    PARAM_WEIGHTS = {
        'vibration': 0.40,
        'g_load': 0.35,
        'control_asymmetry': 0.25
    }
    
    # Event detection thresholds
    EVENT_WINDOW_SIZE = 10
    EVENT_CONFIDENCE_THRESHOLD = 0.7
    
    def __init__(self):
        self.event_history = []
        self.thresholds = self._initialize_thresholds()
        
    def _initialize_thresholds(self) -> Dict[str, Dict]:
        """Initialize thresholds with aviation safety factors"""
        return {
            'vibration': {
                'warning': StructuralFailureThresholds.VIBRATION_MAX * 0.4,
                'critical': StructuralFailureThresholds.VIBRATION_MAX * 0.6
            },
            'control_asymmetry': {
                'warning': StructuralFailureThresholds.CONTROL_ASYMMETRY_MAX * 0.3,
                'critical': StructuralFailureThresholds.CONTROL_ASYMMETRY_MAX * 0.5
            },
            'g_load': {
                'warning': StructuralFailureThresholds.G_LOAD_FACTOR_DIVISOR * 0.5,
                'critical': StructuralFailureThresholds.G_LOAD_FACTOR_DIVISOR * 0.7
            }
        }

    def detect(self, telemetry: Dict[str, float]) -> StructuralDiagnostic:
        """Detect structural failure with event-based confirmation"""
        diagnostics = {}
        failed_components = []
        confidence = 0.0
        max_severity = StructuralFailureSeverity.NORMAL
        status_message = "Normal structural integrity"
        
        # Get control surface values for asymmetry calculation
        aileron = telemetry.get('aileron', 0.0)
        elevator = telemetry.get('elevator', 0.0)
        rudder = telemetry.get('rudder', 0.0)
        
        # Calculate control asymmetry
        telemetry['control_asymmetry'] = abs(aileron) + abs(elevator) + abs(rudder)
        
        # Check each structural parameter
        for param, thresholds in self.thresholds.items():
            value = telemetry.get(param, None)
            status = self._check_parameter(param, value, thresholds)
            diagnostics[param] = status
            
            # Only consider WARNING or higher for confidence
            if status['severity'] >= StructuralFailureSeverity.WARNING:
                severity_value = status['severity'].value
                severity_factor = severity_value - 1  # 1 for WARNING, 2 for CRITICAL, 3 for EMERGENCY
                confidence += self.PARAM_WEIGHTS.get(param, 0.1) * severity_factor
                
                if status['severity'] >= StructuralFailureSeverity.CRITICAL:
                    failed_components.append(param)
                
                if status['severity'] > max_severity:
                    max_severity = status['severity']
        
        # Update event history
        self.event_history.append(confidence)
        if len(self.event_history) > self.EVENT_WINDOW_SIZE:
            self.event_history.pop(0)
        
        # Calculate event confidence (average of last n readings)
        event_confidence = sum(self.event_history) / len(self.event_history) if self.event_history else 0
        
        # Determine failure state conservatively
        is_failure = (max_severity >= StructuralFailureSeverity.CRITICAL and
                     event_confidence >= self.EVENT_CONFIDENCE_THRESHOLD)
        
        # Set status message
        if is_failure:
            status_message = "STRUCTURAL FAILURE CONFIRMED!"
        elif max_severity >= StructuralFailureSeverity.CRITICAL:
            status_message = "Potential structural compromise"
        elif event_confidence > 0.3:
            status_message = "Structural stress detected"
        
        return StructuralDiagnostic(
            is_failure=is_failure,
            severity=max_severity,
            confidence=min(1.0, confidence),
            diagnostics=diagnostics,
            failed_components=failed_components,
            status_message=status_message
        )

    def _check_parameter(self, param: str, value: Optional[float], 
                         thresholds: dict) -> dict:
        """Evaluate structural parameter with aviation-grade thresholds"""
        if value is None:
            return {
                'value': None,
                'status': 'NO_DATA',
                'severity': StructuralFailureSeverity.ADVISORY,
                'message': 'Sensor data unavailable',
                'warning_threshold': thresholds.get('warning'),
                'critical_threshold': thresholds.get('critical')
            }
            
        # Get threshold values
        warning_threshold = thresholds.get('warning')
        critical_threshold = thresholds.get('critical')
        
        # Initialize with normal state
        status = 'NORMAL'
        severity = StructuralFailureSeverity.NORMAL
        message = f"{param.replace('_', ' ').title()} normal"
        
        # Check critical thresholds first (conservative approach)
        if critical_threshold is not None and value >= critical_threshold:
            status = 'CRITICAL'
            severity = StructuralFailureSeverity.EMERGENCY
            message = (f"{param.replace('_', ' ').title()} critical: {value:.1f} "
                      f"(Threshold: {critical_threshold})")
        # Only check warnings if not critical
        elif warning_threshold is not None and value >= warning_threshold:
            status = 'WARNING'
            severity = StructuralFailureSeverity.WARNING
            message = (f"{param.replace('_', ' ').title()} warning: {value:.1f} "
                      f"(Threshold: {warning_threshold})")
        
        return {
            'value': value,
            'status': status,
            'severity': severity,
            'message': message,
            'warning_threshold': warning_threshold,
            'critical_threshold': critical_threshold
        }

# Singleton instance
STRUCTURAL_FAILURE_DETECTOR = StructuralFailureDetector()

def detect_structural_failure(telemetry: Dict[str, float]) -> StructuralDiagnostic:
    """Detect structural failure with aviation-grade diagnostics"""
    return STRUCTURAL_FAILURE_DETECTOR.detect(telemetry)
