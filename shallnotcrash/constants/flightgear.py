"""shallnotcrash/constants/flightgear.py"""

class FGProps:
    #------------------------------------------------------------------------------
    # ESSENTIAL PROPERTIES FOR AUTONOMOUS LANDING (CESSNA 172P)
    #------------------------------------------------------------------------------

    #--------------------------
    # FUEL STATE
    #--------------------------
    class FUEL:
        LEFT_QTY_GAL = "/consumables/fuel/tank[0]/level-gal_us"
        RIGHT_QTY_GAL = "/consumables/fuel/tank[1]/level-gal_us"
        LEFT_CAPACITY = "/consumables/fuel/tank[0]/capacity-gal_us" 
        RIGHT_CAPACITY = "/consumables/fuel/tank[1]/capacity-gal_us"
        TOTAL_GAL = "/consumables/fuel/total-gal_us"
        TOTAL_LBS = "/consumables/fuel/total-fuel-lbs"
    
    #--------------------------
    # ENGINE STATE
    #--------------------------
    class ENGINE:
        RPM = "/engines/engine[0]/rpm"
        EGT_F = "/engines/engine[0]/egt-degf"
        CHT_F = "/engines/engine[0]/cht-degf"
        OIL_TEMP_F = "/engines/engine[0]/oil-temperature-degf"
        OIL_PRESS_PSI = "/engines/engine[0]/oil-pressure-psi"
        FUEL_FLOW_GPH = "/engines/engine[0]/fuel-flow-gph"
        RUNNING = "/engines/engine[0]/running"
        THROTTLE = "/controls/engines/engine[0]/throttle"
        MIXTURE = "/controls/engines/engine[0]/mixture"

    #--------------------------
    # FLIGHT STATE
    #--------------------------
    class FLIGHT:
        # Position
        LATITUDE_DEG = "/position/latitude-deg"
        LONGITUDE_DEG = "/position/longitude-deg"
        ALTITUDE_FT = "/position/altitude-ft"
        ALTITUDE_AGL_FT = "/position/altitude-agl-ft"
        GROUND_ELEV_FT = "/position/ground-elev-ft"

        # Orientation
        ROLL_DEG = "/orientation/roll-deg"
        PITCH_DEG = "/orientation/pitch-deg"
        HEADING_DEG = "/orientation/heading-deg"
        ROLL_RATE_DEGPS = "/orientation/roll-rate-degps"
        PITCH_RATE_DEGPS = "/orientation/pitch-rate-degps"
        YAW_RATE_DEGPS = "/orientation/yaw-rate-degps"
        SIDE_SLIP_DEG = "/orientation/side-slip-deg"
        ALPHA_DEG = "/orientation/alpha-deg"

        # Velocities
        AIRSPEED_KT = "/velocities/airspeed-kt"
        VERTICAL_SPEED_FPS = "/velocities/vertical-speed-fps"
        MACH = "/velocities/mach"
        SPEED_NORTH_FPS = "/velocities/speed-north-fps"
        SPEED_EAST_FPS = "/velocities/speed-east-fps"
        SPEED_DOWN_FPS = "/velocities/speed-down-fps"

        # Accelerations
        ACCEL_NLF = "/accelerations/nlf"
        ACCEL_X_FPS2 = "/accelerations/pilot/x-accel-fps_sec"
        ACCEL_Y_FPS2 = "/accelerations/pilot/y-accel-fps_sec"
        ACCEL_Z_FPS2 = "/accelerations/pilot/z-accel-fps_sec"


    #--------------------------
    # FLIGHT CONTROLS
    #--------------------------
    AILERON = "/controls/flight/aileron"
    ELEVATOR = "/controls/flight/elevator"
    RUDDER = "/controls/flight/rudder"
    ELEVATOR_TRIM = "/controls/flight/elevator-trim"
    FLAPS = "/controls/flight/flaps"  # 0-1 (0=up, 1=full)

    #--------------------------
    # LANDING SYSTEMS
    #--------------------------
    # Gear status (C172 has fixed gear, but useful for simulation)
    GEAR_DOWN = "/instrumentation/annunciators/gear/down"  # Always true for C172

    # Brakes
    BRAKE_LEFT = "/controls/gear/brake-left"
    BRAKE_RIGHT = "/controls/gear/brake-right"
    BRAKE_PARKING = "/controls/gear/brake-parking"

    #--------------------------
    # NAVIGATION AIDS
    #--------------------------
    NAV_FREQ_MHZ = "/instrumentation/nav[0]/frequencies/selected-mhz"
    NAV_RADIAL_DEG = "/instrumentation/nav[0]/radials/actual-deg"
    NAV_DISTANCE = "/instrumentation/nav[0]/nav-distance"
    NAV_GS_NEEDLE_DEFLECTION = "/instrumentation/nav[0]/gs-needle-deflection"  # For ILS

    #--------------------------
    # AUTOPILOT INTERFACE
    #--------------------------
    AP_ENABLED = "/instrumentation/annunciators/autoflight/ap/enabled"
    AP_MODE_NAV = "/instrumentation/annunciators/autoflight/ap/mode/nav"
    AP_MODE_APR = "/instrumentation/annunciators/autoflight/ap/mode/apr"

    #--------------------------
    # SAFETY SYSTEMS
    #--------------------------
    MASTER_CAUTION = "/instrumentation/annunciators/master-caution/state"
    MASTER_WARNING = "/instrumentation/annunciators/master-warning/state"
    ENGINE_OIL_PRESSURE_PSI = "/engines/engine[0]/oil-pressure-psi"
    FUEL_PRESSURE_LOW = "/instrumentation/annunciators/systems/fuel/pressure-low"

    #--------------------------
    # SIMULATION CONTROL
    #--------------------------
    SIM_SPEEDUP = "/sim/speedup"  # Useful for testing