"""shallnotcrash/constants/flightgear.py"""

class FGProps:
    #------------------------------------------------------------------------------
    # ESSENTIAL PROPERTIES FOR AUTONOMOUS LANDING (CESSNA 172P)
    #------------------------------------------------------------------------------

    #--------------------------
    # AIRCRAFT STATE
    #--------------------------
    ALTITUDE_FT = "/position/altitude-ft"
    ALTITUDE_AGL_FT = "/position/altitude-agl-ft"
    GROUND_ELEV_FT = "/position/ground-elev-ft"
    LATITUDE_DEG = "/position/latitude-deg"
    LONGITUDE_DEG = "/position/longitude-deg"

    ROLL_DEG = "/orientation/roll-deg"
    PITCH_DEG = "/orientation/pitch-deg"
    HEADING_DEG = "/orientation/heading-deg"

    AIRSPEED_KT = "/velocities/airspeed-kt"
    VERTICAL_SPEED_FPS = "/velocities/vertical-speed-fps"

    #--------------------------
    # ENGINE PARAMETERS
    #--------------------------
    ENGINE_RPM = "/engines/engine[0]/rpm"
    ENGINE_THROTTLE = "/controls/engines/engine[0]/throttle"
    ENGINE_MIXTURE = "/controls/engines/engine[0]/mixture"
    ENGINE_RUNNING = "/engines/engine[0]/running"

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