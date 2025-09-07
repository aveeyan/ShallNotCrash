#!/usr/bin/env python3
"""
Pattern Types and Data Models
Core definitions for emergency pattern recognition system
"""
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import IntEnum

class EmergencyPattern(IntEnum):
    """Emergency patterns identified by ML models"""
    NORMAL = 0
    ENGINE_DEGRADATION = 1
    FUEL_LEAK = 2
    STRUCTURAL_FATIGUE = 3
    ELECTRICAL_FAILURE = 4
    WEATHER_DISTRESS = 5
    SYSTEM_CASCADE = 6
    UNKNOWN_EMERGENCY = 7

class PatternConfidence(IntEnum):
    """Confidence levels for pattern recognition"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

class AnomalySeverity(IntEnum):
    """Severity levels for anomalies"""
    NORMAL = 0
    MINOR = 1
    MODERATE = 2
    CRITICAL = 3
    EMERGENCY = 4

@dataclass
class AnomalyScore:
    """Anomaly detection result"""
    is_anomaly: bool
    normalized_score: float
    severity: AnomalySeverity
    threshold: float = 0.5
    
    def __post_init__(self):
        if self.normalized_score > 0.9:
            self.severity = AnomalySeverity.EMERGENCY
        elif self.normalized_score > 0.7:
            self.severity = AnomalySeverity.CRITICAL
        elif self.normalized_score > 0.5:
            self.severity = AnomalySeverity.MODERATE
        elif self.normalized_score > 0.3:
            self.severity = AnomalySeverity.MINOR
        else:
            self.severity = AnomalySeverity.NORMAL

@dataclass
class PatternResult:
    """ML pattern recognition result"""
    pattern_type: EmergencyPattern
    confidence: PatternConfidence
    probability: float
    contributing_features: List[str]
    time_to_critical: Optional[float] = None
    recommended_action: str = "Monitor situation"
    severity_trend: float = 0.0
    anomaly_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

@dataclass
class TelemetryData:
    """Standardized telemetry data structure"""
    rpm: float = 0.0
    oil_pressure: float = 0.0
    fuel_flow: float = 0.0
    cht: float = 0.0  # Cylinder Head Temperature
    vibration: float = 0.0
    altitude: float = 0.0
    airspeed: float = 0.0
    engine_temp: float = 0.0
    fuel_level: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for compatibility"""
        return {
            'rpm': self.rpm,
            'oil_pressure': self.oil_pressure,
            'fuel_flow': self.fuel_flow,
            'cht': self.cht,
            'vibration': self.vibration,
            'altitude': self.altitude,
            'airspeed': self.airspeed,
            'engine_temp': self.engine_temp,
            'fuel_level': self.fuel_level
        }

# Emergency pattern signatures for rule-based fallback
EMERGENCY_SIGNATURES = {
    EmergencyPattern.ENGINE_DEGRADATION: {
        'features': ['rpm_trend', 'oil_pressure_trend', 'vibration_increase'],
        'thresholds': {'rpm_trend': -50, 'oil_pressure_trend': -5, 'vibration_increase': 2.0},
        'action': 'REDUCE POWER - Prepare for engine failure'
    },
    EmergencyPattern.FUEL_LEAK: {
        'features': ['fuel_flow_asymmetry', 'fuel_level_drop_rate'],
        'thresholds': {'fuel_flow_asymmetry': 0.3, 'fuel_level_drop_rate': 2.0},
        'action': 'FUEL EMERGENCY - Land immediately'
    },
    EmergencyPattern.STRUCTURAL_FATIGUE: {
        'features': ['vibration_pattern', 'control_asymmetry', 'g_load_variance'],
        'thresholds': {'vibration_pattern': 1.5, 'control_asymmetry': 0.2, 'g_load_variance': 0.5},
        'action': 'STRUCTURAL CONCERN - Reduce G-loads'
    },
    EmergencyPattern.ELECTRICAL_FAILURE: {
        'features': ['electrical_load_variance', 'system_voltage_drop'],
        'thresholds': {'electrical_load_variance': 0.3, 'system_voltage_drop': 2.0},
        'action': 'ELECTRICAL EMERGENCY - Use backup systems'
    },
    EmergencyPattern.WEATHER_DISTRESS: {
        'features': ['turbulence_intensity', 'altitude_deviation'],
        'thresholds': {'turbulence_intensity': 2.0, 'altitude_deviation': 500},
        'action': 'WEATHER EMERGENCY - Seek alternate route'
    },
    EmergencyPattern.SYSTEM_CASCADE: {
        'features': ['multi_system_correlation', 'failure_cascade_rate'],
        'thresholds': {'multi_system_correlation': 0.8, 'failure_cascade_rate': 3.0},
        'action': 'MULTIPLE SYSTEM FAILURE - Emergency landing'
    },
    EmergencyPattern.UNKNOWN_EMERGENCY: {
        'features': ['anomaly_persistence', 'system_instability'],
        'thresholds': {'anomaly_persistence': 0.7, 'system_instability': 0.5},
        'action': 'UNKNOWN EMERGENCY - Assess situation'
    },
    EmergencyPattern.NORMAL: {
        'features': [],
        'thresholds': {},
        'action': 'Continue normal operations'
    }
}

def get_pattern_action(pattern: EmergencyPattern, confidence: PatternConfidence) -> str:
    """Generate recommended actions based on pattern and confidence"""
    base_action = EMERGENCY_SIGNATURES[pattern]['action']
    
    if confidence == PatternConfidence.VERY_HIGH and pattern != EmergencyPattern.NORMAL:
        return f"IMMEDIATE ACTION: {base_action}"
    
    return base_action
