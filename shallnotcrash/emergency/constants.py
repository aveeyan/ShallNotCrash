#!/usr/bin/env python3
"""
Emergency detection constants for Cessna 172P
Integrated with FGProps and C172P operational limits
"""
from enum import Enum, auto
from ..airplane.constants import C172PConstants
from ..constants.flightgear import FGProps

class EmergencySeverity(Enum):
    """Standardized emergency classification per FAA AC 25-7"""
    ADVISORY = auto()  # Abnormal condition requiring awareness
    WARNING = auto()   # Imminent threat requiring preparation
    CRITICAL = auto()  # Immediate action required
    EMERGENCY = auto() # Mayday situation (loss of control imminent)

# ====================== DETECTION THRESHOLDS ======================
class EngineThresholds:
    # ============= RPM CONSTANTS =============
    RPM = {
        'MIN': 800,
        'MAX': 2700,
        'FAILURE': 500
    }
    
    # ============= OIL PRESSURE CONSTANTS =============
    OIL_PRESS = {
        'MIN': 20,
        'MAX': 60,
        'CRITICAL': 15
    }
    
    # ============= CHT CONSTANTS =============
    CHT = {
        'MIN': 300,
        'MAX': 450,
        'CRITICAL': 500,
        'WARNING': C172PConstants.ENGINE['MAX_CHT'] - 50,
        'RECOVERY_TARGET': 400
    }
    
    # ============= EGT CONSTANTS =============
    EGT = {
        'MIN': 800,
        'MAX': 1400,
        'CRITICAL': 1500
    }
    
    # ============= OIL TEMPERATURE CONSTANTS =============
    OIL_TEMP = {
        'MIN': 100,
        'MAX': 245,
        'CRITICAL': 260,
        'WARNING': C172PConstants.ENGINE['MAX_OIL_TEMP'] - 15,
    }
    
    # ============= VIBRATION CONSTANTS =============
    VIBRATION = {
        'WARNING': 0.3,
        'CRITICAL': 0.5
    }
    
    # ============= FUEL FLOW CONSTANTS =============
    FUEL_FLOW = {
        'MIN_IDLE': C172PConstants.ENGINE['MIN_FUEL_FLOW_IDLE'],
        'MAX_NORMAL': C172PConstants.ENGINE['MAX_FUEL_FLOW']
    }
    
    # ============= CARBURETOR ICING CONSTANTS =============
    CARB_ICE = {
        'OAT_MAX_RISK': 10,
        'HUMIDITY_MIN': 60,
        'RPM_DROP_WARNING': 150,
        'RPM_DROP_CRITICAL': 300,
        'RECOVERY_TIME': 90
    }
    
    # ============= RESTART CONSTANTS =============
    RESTART = {
        'MIN_ALTITUDE': C172PConstants.EMERGENCY['RESTART_MIN_ALT'],
        'MAX_ATTEMPTS': 3,
        'ATTEMPT_INTERVAL': 30
    }
    
    # ============= OIL SYSTEM CONSTANTS =============
    OIL = {
        'TEMP_WARNING': C172PConstants.ENGINE['MAX_OIL_TEMP'] - 15,
        'TEMP_CRITICAL': C172PConstants.ENGINE['MAX_OIL_TEMP'],
        'PRESS_IDLE_MIN': C172PConstants.ENGINE['MIN_OIL_PRESS_IDLE'],
        'PRESS_RUN_MIN': C172PConstants.ENGINE['MIN_OIL_PRESS_RUNNING']
    }

class FuelThresholds:
    """Fuel quantity and balance limits (per POH Section 7)"""
    
    QTY = {
        'WARNING': C172PConstants.FUEL['WARNING_THRESHOLD_GAL'],  # 10gal
        'CRITICAL': C172PConstants.FUEL['CRITICAL_THRESHOLD_GAL'], # 5gal
        'MIN_SINGLE_TANK': 2  # gal (per tank minimum)
    }
    
    IMBALANCE = {
        'WARNING': C172PConstants.FUEL['MAX_IMBALANCE_GAL'],  # 5gal
        'CRITICAL': C172PConstants.FUEL['MAX_IMBALANCE_GAL'] * 2  # 10gal
    }

    STARVATION = {
        'FLOW_WARNING': 1.5,    # GPH
        'FLOW_CRITICAL': 1.0    # GPH
    }

class AerodynamicThresholds:
    """Flight envelope protection limits (per POH Section 4)"""
    
    STALL = {
        'SPEED_BUFFER': 5,  # kt above VS0
        'VSI_CRITICAL': -500,  # ft/min
        'ALTITUDE_BUFFER': 1000  # ft AGL
    }
    
    OVERSPEED = {
        'WARNING': C172PConstants.SPEEDS['VNO'],  # 129kt
        'CRITICAL': C172PConstants.SPEEDS['VNE']   # 163kt
    }

# ====================== FLIGHTGEAR PROPERTY PATHS ======================
class FGEmergencyPaths:
    """Critical FlightGear properties for emergency detection"""
    
    # Direct annunciators
    ENGINE_FIRE = FGProps.ANNUNCIATORS.ENGINE_FIRE
    OIL_PRESS_WARN = FGProps.ANNUNCIATORS.OIL_PRESS_LOW
    
    # Environmental
    OAT_C = FGProps.ENVIRONMENT.OAT_C
    HUMIDITY = FGProps.ENVIRONMENT.HUMIDITY
    
    # System states
    CARB_HEAT = FGProps.ENGINE.CARB_HEAT
    FUEL_SELECTOR = FGProps.FUEL.SELECTOR

# ====================== RESPONSE CONFIGURATION ======================
class EmergencyConfig:
    """System behavior parameters"""
    
    TELEMETRY_RATE = 10  # Hz
    DEBOUNCE_TIME = {
        EmergencySeverity.CRITICAL: 1.0,  # sec
        EmergencySeverity.WARNING: 3.0,
        EmergencySeverity.ADVISORY: 5.0
    }
    
    # Alert persistence
    MIN_ALERT_DURATION = 5.0  # sec

# ====================== TEST PARAMETERS ======================
class TestThresholds:
    """Values for simulation testing only"""
    ENGINE_FAILURE_RPM = 200  # RPM
    STALL_TEST_ALT = 3000  # ft AGL

# ====================== EMERGENCY PROCEDURES ======================
class EmergencyProcedures:
    """Timing and sequencing for emergency actions"""
    ENGINE_FAILURE = {
        'ACTION_DELAYS': {
            'MAGNETO_CHECK': 5,      # Seconds
            'FUEL_SELECTOR_CHANGE': 2,
            'RESTART_ATTEMPT_DURATION': 10
        },
        'ALTITUDE_LOSS_RATE': 700,    # ft/min during descent
        'MIN_FINAL_ALT': 500          # ft AGL for final approach
    }
    FUEL_EMERGENCY = {
        'TANK_SWITCH_INTERVAL': 5,          # Minutes
        'PUMP_DURATION': 10,                # Seconds
        'MIXTURE_HOLD': 5,                  # Seconds
        'THROTTLE_CYCLE_INTERVAL': 15,      # Seconds
        'MIN_ENDURANCE_WARNING': 30         # Minutes
    }

class StructuralFailureThresholds:
    """Thresholds for structural failure detection and response"""
    # Control system parameters
    CONTROL_ASYMMETRY_MAX = 3.0
    CONTROL_EFFECTIVENESS_THRESHOLD = 0.5
    
    # Structural integrity parameters
    VIBRATION_FACTOR_DIVISOR = 5.0
    G_LOAD_FACTOR_DIVISOR = 2.0
    STRUCTURAL_INTEGRITY_MIN = 0.3
    STRUCTURAL_INTEGRITY_MAX = 0.7
    
    # Landing parameters
    MIN_LANDING_ALT = 500    # ft AGL
    MAX_LANDING_DISTANCE = 5  # NM
    
    # Vibration limits
    VIBRATION_MAX = 10.0  # Maximum detectable vibration
    VIBRATION_WARNING = VIBRATION_MAX * 0.6
    VIBRATION_CRITICAL = VIBRATION_MAX * 0.8
    CONTROL_ASYMMETRY_WARNING = CONTROL_ASYMMETRY_MAX * 0.5
    G_LOAD_WARNING = G_LOAD_FACTOR_DIVISOR * 0.7

