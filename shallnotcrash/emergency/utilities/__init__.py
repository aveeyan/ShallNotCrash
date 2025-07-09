#!/usr/bin/env python3
"""
Emergency Detection Utilities
Provides advanced analytical tools for emergency detection systems
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.emergency.utilities.anomaly_detector import (
    AnomalyDetector,
    AnomalyScore,
    detect_anomalies,
    FlightPhase  # Add this import
)

from shallnotcrash.emergency.utilities.correlation_analyzer import (
    CorrelationAnalyzer,
    CorrelationDiagnostic,
    CorrelationLevel,
    analyze_system_correlations
)

from shallnotcrash.emergency.utilities.pattern_recognizer import (
    PatternRecognizer,
    recognize_emergency_patterns
)

# Public API
__all__ = [
    # Anomaly Detection
    'AnomalyDetector',
    'AnomalyScore',
    'detect_anomalies',
    'FlightPhase',  # Add this to __all__
    
    # Correlation Analysis
    'CorrelationAnalyzer',
    'CorrelationDiagnostic',
    'CorrelationLevel',
    'analyze_system_correlations',
    
    # Pattern Recognition
    'PatternRecognizer',
    'recognize_emergency_patterns'
]