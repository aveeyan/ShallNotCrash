from shallnotcrash.constants.connection import FGConnectionConstants
from shallnotcrash.constants.flightgear import FGProps

class C172PConstants:
    """Complete operational limits for Cessna 172P (Lycoming O-320-D2J)"""
    
    # ===== PERFORMANCE LIMITS =====
    SPEEDS = {  # In knots (KCAS)
        'VNE': 163,     # Never exceed
        'VNO': 129,     # Max structural cruise
        'VS0': 48,      # Stall speed (flaps down)
        'VFE': 85       # Max flaps extended
    }
    
    # ===== FUEL SYSTEM ===== 
    FUEL = {
        'TANK_COUNT': 2,
        'TOTAL_CAPACITY_GAL': 56,
        'USABLE_CAPACITY_GAL': 53,
        'DENSITY_PPG': 6.0,         # 6 lbs/gal for 100LL
        'WARNING_THRESHOLD_GAL': 10,
        'CRITICAL_THRESHOLD_GAL': 5,
        'MAX_IMBALANCE_GAL': 5
    }
    
    # ===== ENGINE (Lycoming O-320-D2J) =====
    ENGINE = {
        # RPM Limits
        'MAX_RPM': 2700,            # Absolute maximum
        'REDLINE_RPM': 2500,        # Continuous operation limit
        'IDLE_RPM': 600,            # Normal idle range
        'MIN_RUNNING_RPM': 300,     # Below this = engine failure
        
        # Temperature Limits (°F)
        'MAX_EGT': 1650,            # Exhaust Gas Temp
        'MAX_CHT': 500,             # Cylinder Head Temp
        'MAX_OIL_TEMP': 245,
        'MIN_OIL_TEMP': 75,         # For takeoff
        
        # Oil Pressure (PSI)
        'MIN_OIL_PRESS_IDLE': 10,
        'MIN_OIL_PRESS_RUNNING': 20,
        'MAX_OIL_PRESS': 90,
        
        # Fuel Flow (GPH)
        'MIN_FUEL_FLOW_IDLE': 2.0,
        'MAX_FUEL_FLOW': 15.0,
        
        # Maintenance Intervals (hours)
        'OIL_CHANGE_INTERVAL': 50
    }
    
    # ===== REUSED CONSTANTS =====
    CONNECTION = FGConnectionConstants
    PROPERTIES = FGProps