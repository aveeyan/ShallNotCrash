#!/usr/bin/env python3
"""
Robust Anomaly Detection for Flight Systems
Integrated with emergency protocols standards
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import IntEnum, auto
import time
from collections import defaultdict
import warnings
from .. import constants  # Updated import path

class FlightPhase(IntEnum):
    """Flight phases with integer values for severity comparison"""
    UNKNOWN = 0
    TAKEOFF = 1
    CLIMB = 2
    CRUISE = 3
    DESCENT = 4
    LANDING = 5

class AnomalySeverity(IntEnum):
    """Standardized severity levels matching emergency protocols"""
    NORMAL = 0
    ADVISORY = 1
    WARNING = 2
    CRITICAL = 3
    EMERGENCY = 4

@dataclass
class AnomalyScore:
    """Enhanced anomaly detection result with protocol alignment"""
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

class DetectionMode(IntEnum):
    """Detection methods with integer values"""
    Z_SCORE = 0
    MODIFIED_Z = 1
    IQR = 2

class AnomalyDetector:
    """Enhanced anomaly detection integrated with emergency protocols"""
    
    def __init__(self, mode: DetectionMode = DetectionMode.MODIFIED_Z):
        self.PARAM_WEIGHTS = constants.SystemWeights.PARAMETERS
        self.PHASE_THRESHOLDS = constants.DetectionParameters.Z_SCORE_THRESHOLDS
        self.mode = mode
        self.phase_models = {
            phase: defaultdict(lambda: {
                'values': [],
                'stats': None,
                'last_updated': 0
            })
            for phase in FlightPhase
        }
        self.MIN_SAMPLES = 30  # Minimum samples required for detection
        self.WARMUP_SAMPLES = 100  # Samples required before model adaptation
        self.DEFAULT_THRESHOLDS = {
            FlightPhase.TAKEOFF: 2.8,
            FlightPhase.CLIMB: 3.0,
            FlightPhase.CRUISE: 3.2,
            FlightPhase.DESCENT: 3.0,
            FlightPhase.LANDING: 2.5,
            FlightPhase.UNKNOWN: 3.0
        }
        self._init_thresholds()
    
    def _init_thresholds(self):
        """Initialize adaptive thresholds with emergency protocol alignment"""
        self.dynamic_thresholds = {
            phase: {
                'base': threshold,
                'current': threshold,
                'trend': 0.0
            }
            for phase, threshold in self.DEFAULT_THRESHOLDS.items()
        }
    
    def _mad(self, data):
        """Median Absolute Deviation implementation"""
        median = np.median(data)
        return np.median(np.abs(data - median))
    
    def train(self, training_data: Dict[FlightPhase, Dict[str, List[float]]]):
        """Train statistical models with protocol-aligned validation"""
        for phase, params in training_data.items():
            for param, values in params.items():
                if len(values) >= self.MIN_SAMPLES and self._validate_parameter(param):
                    self._update_model(phase, param, values)
    
    def _update_model(self, phase: FlightPhase, param: str, values: List[float]):
        """Update model with outlier removal and protocol checks"""
        values = np.array(values)
        
        # Outlier removal during training
        if len(values) > self.WARMUP_SAMPLES:
            q1, q3 = np.percentile(values, [25, 75])
            iqr = q3 - q1
            mask = (values >= (q1 - 1.5*iqr)) & (values <= (q3 + 1.5*iqr))
            values = values[mask]
        
        stats = {
            'mean': float(np.mean(values)),
            'median': float(np.median(values)),
            'std': max(float(np.std(values)), 0.01),
            'mad': max(float(self._mad(values)), 0.01),
            'q1': float(np.percentile(values, 25)),
            'q3': float(np.percentile(values, 75)),
            'count': len(values)
        }
        
        self.phase_models[phase][param]['stats'] = stats
        self.phase_models[phase][param]['last_updated'] = time.time()
    
    def detect(self, 
              telemetry: Dict[str, float], 
              flight_phase: FlightPhase = FlightPhase.UNKNOWN) -> Dict[str, AnomalyScore]:
        """Detect anomalies with emergency protocol integration"""
        results = {}
        current_phase = self._validate_phase(flight_phase)
        
        for param, value in telemetry.items():
            if not self._validate_parameter(param) or not self._validate_value(param, value):
                continue
                
            model = self.phase_models[current_phase][param]
            
            if model['stats'] is None and len(model['values']) >= self.MIN_SAMPLES:
                self._update_model(current_phase, param, model['values'])
            
            score = self._calculate_anomaly_score(param, value, current_phase)
            results[param] = score
            
            self._update_parameter_history(param, value, current_phase, score.normalized_score)
        
        return results
    
    def _calculate_anomaly_score(self, param: str, value: float, phase: FlightPhase) -> AnomalyScore:
        """Calculate score with protocol-aligned severity levels"""
        model = self.phase_models[phase][param]
        stats = model['stats']
        
        if stats is None:
            return AnomalyScore(
                parameter=param,
                value=value,
                baseline=value,
                deviation=0.0,
                normalized_score=0.0,
                is_anomaly=False,
                severity=AnomalySeverity.NORMAL,
                flight_phase=phase,
                confidence=0.0,
                status_message="Insufficient data for detection"
            )
        
        if self.mode == DetectionMode.Z_SCORE:
            baseline = stats['mean']
            deviation = stats['std']
            score = abs(value - baseline) / deviation if deviation != 0 else 0.0
            
        elif self.mode == DetectionMode.MODIFIED_Z:
            baseline = stats['median']
            deviation = stats['mad'] * 1.4826
            score = abs(value - baseline) / deviation if deviation != 0 else 0.0
            
        elif self.mode == DetectionMode.IQR:
            baseline = stats['median']
            iqr = stats['q3'] - stats['q1']
            score = abs(value - baseline) / iqr if iqr != 0 else 0.0
            
        threshold = self.dynamic_thresholds[phase]['current']
        is_anomaly = score > threshold
        
        # Map score to protocol severity levels
        severity = self._score_to_severity(score, threshold)
        status_message = self._get_status_message(param, severity, score)
        
        return AnomalyScore(
            parameter=param,
            value=value,
            baseline=baseline,
            deviation=deviation,
            normalized_score=score,
            is_anomaly=is_anomaly,
            severity=severity,
            flight_phase=phase,
            confidence=self._calculate_confidence(param, phase),
            status_message=status_message
        )
    
    def _score_to_severity(self, score: float, threshold: float) -> AnomalySeverity:
        """Convert statistical score to protocol severity levels"""
        if score > threshold * 2.0:
            return AnomalySeverity.EMERGENCY
        elif score > threshold * 1.5:
            return AnomalySeverity.CRITICAL
        elif score > threshold * 1.2:
            return AnomalySeverity.WARNING
        elif score > threshold:
            return AnomalySeverity.ADVISORY
        return AnomalySeverity.NORMAL
    
    def _get_status_message(self, param: str, severity: AnomalySeverity, score: float) -> str:
        """Generate protocol-aligned status messages"""
        param_name = param.replace('_', ' ').upper()
        messages = {
            AnomalySeverity.NORMAL: f"{param_name} normal",
            AnomalySeverity.ADVISORY: f"{param_name} showing minor deviation",
            AnomalySeverity.WARNING: f"{param_name} out of normal range",
            AnomalySeverity.CRITICAL: f"{param_name} CRITICAL LEVEL",
            AnomalySeverity.EMERGENCY: f"{param_name} EMERGENCY CONDITION!"
        }
        return messages.get(severity, "Status unknown")
    
    def _update_parameter_history(self, param: str, value: float, phase: FlightPhase, score: float):
        """Maintain parameter history with protocol checks"""
        model = self.phase_models[phase][param]
        model['values'].append(value)
        
        if 'scores' not in model:
            model['scores'] = []
        model['scores'].append(score)
        
        if len(model['values']) % self.WARMUP_SAMPLES == 0:
            self._adapt_model(param, phase)
    
    def _adapt_model(self, param: str, phase: FlightPhase):
        """Adapt models with protocol-aligned adjustments"""
        model = self.phase_models[phase][param]
        
        if len(model['values']) >= self.WARMUP_SAMPLES:
            self._update_model(phase, param, model['values'][-self.WARMUP_SAMPLES:])
            
            recent_scores = model['scores'][-100:] if 'scores' in model else []
            if recent_scores:
                anomaly_rate = sum(s > self.dynamic_thresholds[phase]['current'] 
                                 for s in recent_scores) / len(recent_scores)
                adjustment = 0.1 * (0.05 - anomaly_rate)
                new_threshold = self.dynamic_thresholds[phase]['current'] + adjustment
                self.dynamic_thresholds[phase]['current'] = max(1.0, min(5.0, new_threshold))
    
    def _validate_phase(self, phase: FlightPhase) -> FlightPhase:
        """Ensure valid flight phase"""
        return phase if phase in FlightPhase else FlightPhase.UNKNOWN
    
    def _validate_parameter(self, param: str) -> bool:
        """Check if parameter is monitored in protocols"""
        return param in self.PARAM_WEIGHTS
    
    def _validate_value(self, param: str, value: float) -> bool:
        """Validate sensor reading ranges against protocol thresholds"""
        param_ranges = {
            'rpm': (constants.EngineThresholds.RPM['MIN'], constants.EngineThresholds.RPM['MAX']),
            'oil_pressure': (constants.EngineThresholds.OIL_PRESS['MIN'], constants.EngineThresholds.OIL_PRESS['MAX']),
            'fuel_flow': (0, constants.EngineThresholds.FUEL_FLOW['MAX_NORMAL']),
            'cht': (constants.EngineThresholds.CHT['MIN'], constants.EngineThresholds.CHT['MAX']),
            'oil_temp': (constants.EngineThresholds.OIL_TEMP['MIN'], constants.EngineThresholds.OIL_TEMP['MAX']),
            'egt': (constants.EngineThresholds.EGT['MIN'], constants.EngineThresholds.EGT['MAX'])
        }
        if param in param_ranges:
            min_val, max_val = param_ranges[param]
            return min_val <= value <= max_val
        return False
    
    def _calculate_confidence(self, param: str, phase: FlightPhase) -> float:
        """Calculate detection confidence with protocol weights"""
        model = self.phase_models[phase][param]
        if model['stats'] is None:
            return 0.0
        
        sample_count = model['stats']['count']
        base_confidence = min(1.0, sample_count / self.WARMUP_SAMPLES)
        param_weight = self.PARAM_WEIGHTS.get(param, 0.1)
        
        return base_confidence * param_weight

# Singleton instance with C172P configuration
ANOMALY_DETECTOR = AnomalyDetector(mode=DetectionMode.MODIFIED_Z)

def detect_anomalies(telemetry: Dict[str, float], 
                    flight_phase: FlightPhase = FlightPhase.UNKNOWN) -> Dict[str, AnomalyScore]:
    """Public interface for C172P anomaly detection"""
    return ANOMALY_DETECTOR.detect(telemetry, flight_phase)