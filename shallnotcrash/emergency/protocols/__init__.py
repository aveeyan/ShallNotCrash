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
    StructuralFailureProtocol,
    STRUCTURAL_FAILURE_PROTOCOL,
    get_current_stage
)

# Public API
__all__ = [
    # Detectors
    'EngineFailureDetector',
    'FuelEmergencyDetector',
    
    # Diagnostic Functions
    'detect_engine_failure',
    'detect_fuel_emergency',
    
    # Protocol Instances
    'STRUCTURAL_FAILURE_PROTOCOL',
    
    # Utility Functions
    'get_current_stage'
]