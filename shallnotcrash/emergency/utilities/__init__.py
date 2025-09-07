#!/usr/bin/env python3
"""
Emergency Pattern Recognition System for Aircraft
A comprehensive ML-based system for detecting and analyzing emergency patterns in aircraft telemetry data.

This package provides:
- Pattern type definitions and data models
- Feature extraction from telemetry data
- ML-based pattern classification
- Pattern analysis and decision support
- Training utilities for model development

Usage:
    from emergency_pattern_recognition import EmergencyPattern, PatternAnalyzer

    analyzer = PatternAnalyzer()
    result = analyzer.analyze(ml_prediction, features)
"""

__version__ = "1.0.0"
__author__ = "Aircraft Emergency Detection System"
__description__ = "ML-based emergency pattern recognition for aircraft telemetry"

# Core pattern types and data models
from .pattern_recognition.pr1_pattern_types import (
    EmergencyPattern,
    PatternConfidence,
    AnomalySeverity,
    AnomalyScore,
    PatternResult,
    TelemetryData,
    EMERGENCY_SIGNATURES,
    get_pattern_action
)

# Feature extraction
from .pattern_recognition.pr2_feature_extractor import FeatureExtractor

# ML models
from .pattern_recognition.pr3_ml_models import MLModelManager

# Pattern analysis
from .pattern_recognition.pr4_pattern_analyzer import PatternAnalyzer

# Pattern recognition engine (fixed name)
from .pattern_recognizer import recognize_patterns

# Training utilities
from .pattern_recognition.train_emergency_detector import (
    generate_training_data,
    train_and_evaluate_model,
    visualize_data_characteristics
)

# Public API
__all__ = [
    'EmergencyPattern',
    'PatternConfidence',
    'AnomalySeverity',
    'AnomalyScore',
    'PatternResult',
    'TelemetryData',
    'FeatureExtractor',
    'MLModelManager',
    'PatternAnalyzer',
    'recognize_patterns',
    'EMERGENCY_SIGNATURES',
    'get_pattern_action',
    'generate_training_data',
    'train_and_evaluate_model',
    'visualize_data_characteristics',
    '__version__',
    '__author__',
    '__description__'
]

# Optional helpers
def create_emergency_detector():
    """
    Factory function to create a complete emergency detection system.
    
    Returns:
        tuple: (feature_extractor, ml_manager, pattern_analyzer)
    """
    feature_extractor = FeatureExtractor(window_size=30)
    ml_manager = MLModelManager()
    pattern_analyzer = PatternAnalyzer()
    return feature_extractor, ml_manager, pattern_analyzer

def get_pattern_info(pattern: EmergencyPattern) -> dict:
    """
    Get detailed information about a specific emergency pattern.
    
    Args:
        pattern: The emergency pattern to get info for
        
    Returns:
        dict: Pattern information including features, thresholds, and actions
    """
    return EMERGENCY_SIGNATURES.get(pattern, {})

def is_critical_pattern(pattern: EmergencyPattern) -> bool:
    """
    Check if a pattern represents a critical emergency.
    
    Args:
        pattern: The emergency pattern to check
        
    Returns:
        bool: True if pattern is critical, False otherwise
    """
    critical_patterns = {
        EmergencyPattern.FUEL_LEAK,
        EmergencyPattern.STRUCTURAL_FATIGUE,
        EmergencyPattern.ELECTRICAL_FAILURE,
        EmergencyPattern.SYSTEM_CASCADE,
        EmergencyPattern.UNKNOWN_EMERGENCY
    }
    return pattern in critical_patterns

__all__.extend([
    'create_emergency_detector',
    'get_pattern_info',
    'is_critical_pattern'
])

def check_dependencies():
    """Check if required dependencies are available."""
    deps = {}
    try:
        import numpy
        deps['numpy'] = numpy.__version__
    except ImportError:
        deps['numpy'] = 'Not available'

    try:
        import sklearn
        deps['sklearn'] = sklearn.__version__
    except ImportError:
        deps['sklearn'] = 'Not available'

    try:
        import pandas
        deps['pandas'] = pandas.__version__
    except ImportError:
        deps['pandas'] = 'Not available'

    try:
        import matplotlib
        deps['matplotlib'] = matplotlib.__version__
    except ImportError:
        deps['matplotlib'] = 'Not available'

    return deps

__all__.append('check_dependencies')

def _initialize_package():
    """Initialize package-level settings and configurations."""
    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)

_initialize_package()
