#!/usr/bin/env python3
"""
Advanced Engine Failure Detection for Cessna 172P
Provides accurate engine health diagnostics with realistic thresholds
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import IntEnum
import time

# Relative imports within shallnotcrash package
from shallnotcrash.emergency.constants import EngineThresholds

class EngineFailureSeverity(IntEnum):
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
    status_message: str

class EngineFailureDetector:
    """Precise engine failure detection with realistic thresholds"""
    # Optimized parameter importance weights
    PARAM_WEIGHTS = {
        'rpm': 0.25,
        'oil_pressure': 0.22,
        'fuel_flow': 0.20,
        'cht': 0.13,
        'oil_temp': 0.12,
        'egt': 0.08
    }
    
    # Warm-up parameters
    WARM_UP_THRESHOLD = 150  # °F
    MIN_WARM_UP_RPM = 800
    
    def __init__(self):
        self.warm_up_start = time.time()  # Always initialized
        self.warm_up_complete = False
        self.thresholds = self._initialize_thresholds()
        
    def _initialize_thresholds(self) -> Dict[str, Dict]:
        """Initialize thresholds with realistic operational ranges"""
        return {
            'rpm': {
                'normal': (700, 2800),  # Wider range for operational flexibility
                'critical': EngineThresholds.RPM['FAILURE']
            },
            'oil_pressure': {
                'normal': (15, 70),  # Realistic pressure range
                'critical': EngineThresholds.OIL_PRESS['CRITICAL']
            },
            'cht': {
                'normal': (0, 420),  # Upper buffer for normal ops
                'critical': EngineThresholds.CHT['CRITICAL']
            },
            'egt': {
                'normal': (0, 1450),  # Upper buffer
                'critical': EngineThresholds.EGT['CRITICAL']
            },
            'oil_temp': {
                'normal': (0, 230),  # Upper buffer
                'critical': EngineThresholds.OIL_TEMP['CRITICAL']
            },
            'fuel_flow': {
                'normal': (7, 15),  # Realistic flow range
                'critical': EngineThresholds.FUEL_FLOW['MIN_IDLE'] * 0.7
            }
        }

    def detect(self, telemetry: Dict[str, float]) -> EngineDiagnostic:
        """Detect engine failure with accurate diagnostics"""
        # Default status message
        status_message = "Normal operation"
        
        # Track warm-up state
        self._update_warm_up_state(telemetry.get('rpm', 0), 
                                  telemetry.get('cht', 0))
        
        # If engine is off, return immediately
        if telemetry.get('rpm', 0) < 300:
            return EngineDiagnostic(
                is_failure=False,
                severity=EngineFailureSeverity.NORMAL,
                confidence=0.0,
                diagnostics={},
                failed_components=[],
                status_message="Engine off",
            )
        
        diagnostics = {}
        failed_components = []
        confidence = 0.0
        max_severity = EngineFailureSeverity.NORMAL

        # Check each engine parameter
        for param, thresholds in self.thresholds.items():
            value = telemetry.get(param, None)
            status = self._check_parameter(param, value, thresholds)
            diagnostics[param] = status
            
            # Skip warnings during warm-up for temperature parameters
            if (self.warm_up_complete is False and 
                status['severity'] == EngineFailureSeverity.WARNING and
                param in ['cht', 'oil_temp', 'egt']):
                status['severity'] = EngineFailureSeverity.NORMAL
                status['status'] = 'NORMAL'
                status['message'] = f"{param.upper()} warming up"
            
            # Only consider WARNING or higher for failure confidence
            if status['severity'] >= EngineFailureSeverity.WARNING:
                # Improved severity factor calculation
                severity_value = status['severity'].value
                severity_factor = (severity_value - 1) * 0.3  # More impactful
                confidence += self.PARAM_WEIGHTS.get(param, 0.1) * severity_factor
                
                # Track failed components for critical+ issues
                if status['severity'] >= EngineFailureSeverity.CRITICAL:
                    failed_components.append(param)
                
                # Track max severity
                if status['severity'] > max_severity:
                    max_severity = status['severity']
        
        # Determine overall failure state
        is_failure = max_severity >= EngineFailureSeverity.CRITICAL
        confidence = min(1.0, max(0.0, confidence))
        
        # Set status message
        if not self.warm_up_complete:
            duration = int(time.time() - self.warm_up_start)
            status_message = f"Engine warming up ({duration}s)"
        elif is_failure:
            status_message = "ENGINE FAILURE DETECTED!"
        elif confidence > 0.3:
            status_message = "Engine showing signs of stress"
        
        return EngineDiagnostic(
            is_failure=is_failure,
            severity=max_severity,
            confidence=confidence,
            diagnostics=diagnostics,
            failed_components=failed_components,
            status_message=status_message
        )

    def _update_warm_up_state(self, rpm: float, cht: float):
        """Track engine warm-up state with robust initialization"""
        # Always ensure we have a warm-up start time
        if self.warm_up_start is None:
            self.warm_up_start = time.time()
            
        # Update warm-up state
        if rpm < self.MIN_WARM_UP_RPM:
            self.warm_up_complete = False
        elif not self.warm_up_complete and cht > self.WARM_UP_THRESHOLD:
            self.warm_up_complete = True

    def _check_parameter(self, param: str, value: Optional[float], 
                        thresholds: Dict) -> Dict:
        """Evaluate engine parameter with realistic thresholds"""
        if value is None:
            return self._create_status(
                param, None, 'NO_DATA', 
                EngineFailureSeverity.ADVISORY, 
                'Sensor data unavailable'
            )
        
        # Get threshold values
        normal_range = thresholds.get('normal', (0, 1000))
        critical_threshold = thresholds.get('critical', None)
        
        # Initialize severity and message
        severity = EngineFailureSeverity.NORMAL
        status = 'NORMAL'
        message = f"{param.upper()} within normal parameters"
        
        # Check critical thresholds first
        if critical_threshold is not None:
            # For parameters where low is critical
            if param in ['rpm', 'oil_pressure', 'fuel_flow']:
                if value < critical_threshold:
                    status = 'CRITICAL'
                    severity = EngineFailureSeverity.EMERGENCY
                    message = (f"{param.upper()} critically low: {value:.1f} "
                              f"(Threshold: {critical_threshold})")
            
            # For parameters where high is critical
            else:
                if value > critical_threshold:
                    status = 'CRITICAL'
                    severity = EngineFailureSeverity.EMERGENCY
                    message = (f"{param.upper()} critically high: {value:.1f} "
                              f"(Threshold: {critical_threshold})")
        
        # Only check normal range if not already critical
        if status == 'NORMAL' and 'normal' in thresholds:
            low, high = normal_range
            if value < low:
                status = 'WARNING'
                severity = EngineFailureSeverity.WARNING
                message = (f"{param.upper()} low: {value:.1f} "
                          f"(Normal: {low:.1f}-{high:.1f})")
            elif value > high:
                status = 'WARNING'
                severity = EngineFailureSeverity.WARNING
                message = (f"{param.upper()} high: {value:.1f} "
                          f"(Normal: {low:.1f}-{high:.1f})")
        
        return self._create_status(
            param, value, status, severity, message,
            normal_range=thresholds.get('normal'),
            critical_threshold=thresholds.get('critical')
        )
    
    def _create_status(self, param: str, value: Optional[float], status: str,
                      severity: EngineFailureSeverity, message: str,
                      normal_range: Tuple[float, float] = None,
                      critical_threshold: float = None) -> Dict:
        """Create standardized status dictionary"""
        return {
            'value': value,
            'status': status,
            'severity': severity,
            'message': message,
            'normal_range': normal_range,
            'critical_threshold': critical_threshold
        }

# Singleton instance
ENGINE_FAILURE_DETECTOR = EngineFailureDetector()

def detect_engine_failure(telemetry: Dict[str, float]) -> EngineDiagnostic:
    """Detect engine failure with detailed diagnostics"""
    return ENGINE_FAILURE_DETECTOR.detect(telemetry)
