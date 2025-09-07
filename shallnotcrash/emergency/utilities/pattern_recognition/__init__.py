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
    
    # Initialize the system
    analyzer = PatternAnalyzer()
    
    # Process telemetry data
    result = analyzer.analyze(ml_prediction, features)
"""

__version__ = "1.0.0"
__author__ = "Aircraft Emergency Detection System"
__description__ = "ML-based emergency pattern recognition for aircraft telemetry"

# Core pattern types and data models
from .pr1_pattern_types import (
    # Enums
    EmergencyPattern,
    PatternConfidence,
    AnomalySeverity,
    
    # Data classes
    AnomalyScore,
    PatternResult,
    TelemetryData,
    
    # Constants and utilities
    EMERGENCY_SIGNATURES,
    get_pattern_action
)

# Feature extraction
from .pr2_feature_extractor import FeatureExtractor

# ML models
from .pr3_ml_models import MLModelManager

# Pattern analysis
from .pr4_pattern_analyzer import PatternAnalyzer

# Training utilities
from .train_emergency_detector import (
    generate_training_data,
    train_and_evaluate_model,
    visualize_data_characteristics
)

# Public API - main components that users should import
__all__ = [
    # Core types and enums
    'EmergencyPattern',
    'PatternConfidence', 
    'AnomalySeverity',
    
    # Data structures
    'AnomalyScore',
    'PatternResult',
    'TelemetryData',
    
    # Main processing classes
    'FeatureExtractor',
    'MLModelManager',
    'PatternAnalyzer',
    
    # Utilities
    'EMERGENCY_SIGNATURES',
    'get_pattern_action',
    
    # Training functions
    'generate_training_data',
    'train_and_evaluate_model',
    'visualize_data_characteristics',
    
    # Package metadata
    '__version__',
    '__author__',
    '__description__'
]

# Convenience imports for common use cases
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

# Add convenience functions to __all__
__all__.extend([
    'create_emergency_detector',
    'get_pattern_info',
    'is_critical_pattern'
])

# Version compatibility checks
def check_dependencies():
    """
    Check if required dependencies are available.
    
    Returns:
        dict: Status of each dependency
    """
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

# Add to public API
__all__.append('check_dependencies')

# Package initialization
def _initialize_package():
    """Initialize package-level settings and configurations."""
    import warnings
    
    # Filter out common warnings in production
    warnings.filterwarnings('ignore', category=UserWarning)
    warnings.filterwarnings('ignore', category=FutureWarning)
    
    # Set up any package-level constants or configurations
    pass

# Run initialization
_initialize_package()

# Package documentation
__doc__ = """
Emergency Pattern Recognition System for Aircraft Telemetry

This package provides a comprehensive machine learning-based system for detecting 
and analyzing emergency patterns in aircraft telemetry data. The system is designed 
specifically for general aviation aircraft like the Cessna 172P.

Key Features:
- Real-time telemetry data processing
- ML-based pattern recognition with multiple emergency types
- Feature extraction from time-series data
- Confidence scoring and severity assessment
- Training utilities for model development
- Rule-based fallback for unknown patterns

Emergency Patterns Detected:
- Engine degradation
- Fuel leaks
- Structural fatigue
- Electrical failures
- Weather distress
- System cascade failures
- Unknown emergencies

Example Usage:
    # Basic usage
    from emergency_pattern_recognition import create_emergency_detector
    
    # Create system components
    feature_extractor, ml_manager, pattern_analyzer = create_emergency_detector()
    
    # Process telemetry data
    telemetry = TelemetryData(rpm=2200, oil_pressure=32, vibration=1.2)
    features = feature_extractor.extract(telemetry, anomalies, correlations)
    
    # Get ML prediction
    prediction = ml_manager.predict(features)
    
    # Analyze pattern
    result = pattern_analyzer.analyze(prediction, features)
    
    # Check if critical
    if is_critical_pattern(result.pattern_type):
        print(f"CRITICAL: {result.recommended_action}")

For detailed documentation and examples, see the individual module documentation.
"""