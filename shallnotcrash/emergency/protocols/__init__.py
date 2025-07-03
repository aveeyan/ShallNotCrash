#!/usr/bin/env python3
"""
Emergency Protocols Package
Exposes all emergency response protocols with simplified access
"""
from .engine_failure import (
    EngineFailureDetector,
    detect_engine_failure,
    ENGINE_FAILURE_DETECTOR
)
from .fuel_emergency import (
    FuelEmergencyDetector,
    detect_fuel_emergency,
    FUEL_EMERGENCY_DETECTOR
)
from .structural_failure import (
    detect_structural_failure,  # Updated import
    STRUCTURAL_FAILURE_DETECTOR  # Updated import
)

# Public API
__all__ = [
    # Detectors
    'EngineFailureDetector',
    'FuelEmergencyDetector',
    
    # Diagnostic Functions
    'detect_engine_failure',
    'detect_fuel_emergency',
    'detect_structural_failure',  # Added new function
    
    # Detector Instances
    'ENGINE_FAILURE_DETECTOR',
    'FUEL_EMERGENCY_DETECTOR',
    'STRUCTURAL_FAILURE_DETECTOR'  # Added new instance
]