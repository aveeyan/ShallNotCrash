# emergency/tests/test_protocols/test_structural_failure.py
import pytest
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# Now use relative imports
from emergency.protocols.structural_failure import (
    StructuralFailureProtocol,
    STRUCTURAL_FAILURE_PROTOCOL
)
from constants.flightgear import FGProps

# Test data templates
BASE_TELEMETRY = {
    FGProps.FLIGHT.ALTITUDE_FT: 5000,
    FGProps.FLIGHT.AIRSPEED_KT: 100,
    FGProps.CONTROLS.AILERON: 0.0,
    FGProps.CONTROLS.ELEVATOR: 0.0,
    FGProps.CONTROLS.RUDDER: 0.0,
    'vibration_level': 1.0,
    'g_load': 1.2
}

def test_initial_stage():
    """Verify initial stage is Primary Control Loss"""
    protocol = StructuralFailureProtocol()
    actions = protocol.get_actions(BASE_TELEMETRY)
    assert "Primary Control Loss" in actions[0]

def test_stage_transition():
    """Test progression through all stages"""
    protocol = StructuralFailureProtocol()
    
    # Stage 1: Primary Control Loss
    actions = protocol.get_actions(BASE_TELEMETRY)
    assert "PRIMARY CONTROL LOSS" in actions[0]
    
    # Trigger stage 2: Secondary Damage Containment
    stage2_telemetry = {
        **BASE_TELEMETRY,
        'vibration_level': 3.5,  # Above critical threshold
        'control_effectiveness': 0.4  # Below 0.5 threshold
    }
    actions = protocol.get_actions(stage2_telemetry)
    assert "SECONDARY DAMAGE CONTAINMENT" in actions[0]
    
    # Trigger stage 3: Emergency Landing Preparation
    stage3_telemetry = {
        **stage2_telemetry,
        FGProps.FLIGHT.ALTITUDE_FT: 800,
        'distance_to_landing': 3.0
    }
    actions = protocol.get_actions(stage3_telemetry)
    assert "EMERGENCY LANDING PREPARATION" in actions[0]

def test_telemetry_enrichment():
    """Test telemetry enrichment functionality"""
    protocol = StructuralFailureProtocol()
    
    # Create telemetry with control inputs
    telemetry = {
        **BASE_TELEMETRY,
        FGProps.CONTROLS.AILERON: 0.8,
        FGProps.CONTROLS.ELEVATOR: -0.6,
        FGProps.CONTROLS.RUDDER: 0.4
    }
    
    # Check control effectiveness calculation
    enriched = protocol._enrich_telemetry(telemetry)
    assert 0 < enriched['control_effectiveness'] < 1
    
    # Check structural integrity estimation
    assert 0 < enriched['structural_integrity'] < 1

def test_condition_checking():
    """Test condition verification logic"""
    protocol = StructuralFailureProtocol()
    
    # Valid conditions
    assert protocol._check_conditions(
        {'altitude': (0, 10000)},
        {'altitude': 5000}
    ) is True
    
    # Value below range
    assert protocol._check_conditions(
        {'altitude': (1000, 10000)},
        {'altitude': 500}
    ) is False
    
    # Value above range
    assert protocol._check_conditions(
        {'altitude': (0, 1000)},
        {'altitude': 5000}
    ) is False
    
    # Missing parameter
    assert protocol._check_conditions(
        {'altitude': (0, 10000)},
        {}
    ) is False

def test_singleton_reset():
    """Test singleton reset functionality"""
    # Advance protocol to stage 2
    stage2_telemetry = {
        **BASE_TELEMETRY,
        'vibration_level': 4.0,
        'control_effectiveness': 0.3
    }
    STRUCTURAL_FAILURE_PROTOCOL.get_actions(stage2_telemetry)
    assert "SECONDARY DAMAGE CONTAINMENT" in STRUCTURAL_FAILURE_PROTOCOL.get_actions(stage2_telemetry)[0]
    
    # Reset and verify back to initial stage
    STRUCTURAL_FAILURE_PROTOCOL.reset()
    actions = STRUCTURAL_FAILURE_PROTOCOL.get_actions(BASE_TELEMETRY)
    assert "PRIMARY CONTROL LOSS" in actions[0]

def test_structural_integrity_calculation():
    """Test structural integrity estimation logic"""
    protocol = StructuralFailureProtocol()
    
    # Normal conditions
    telemetry = {'vibration_level': 1.0, 'g_load': 1.0}
    integrity = protocol._estimate_structural_integrity(telemetry['vibration_level'], telemetry['g_load'])
    assert 0.9 <= integrity <= 1.0
    
    # High stress conditions
    telemetry = {'vibration_level': 4.5, 'g_load': 2.8}
    integrity = protocol._estimate_structural_integrity(telemetry['vibration_level'], telemetry['g_load'])
    assert 0 < integrity < 0.5
    
    # Extreme conditions
    telemetry = {'vibration_level': 6.0, 'g_load': 3.5}
    integrity = protocol._estimate_structural_integrity(telemetry['vibration_level'], telemetry['g_load'])
    assert integrity == 0.0

def test_control_effectiveness_calculation():
    """Test control effectiveness calculation"""
    protocol = StructuralFailureProtocol()
    
    # Neutral controls
    effectiveness = protocol._calculate_control_effectiveness(0.0, 0.0, 0.0)
    assert effectiveness == 1.0
    
    # Moderate inputs
    effectiveness = protocol._calculate_control_effectiveness(0.5, -0.3, 0.2)
    assert 0.4 < effectiveness < 0.7
    
    # Extreme inputs
    effectiveness = protocol._calculate_control_effectiveness(1.0, -1.0, 0.8)
    assert effectiveness == 0.0