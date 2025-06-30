"""shallnotcrash/constants/flightgear.py"""

class FGProps:
    #------------------------------------------------------------------------------
    # ESSENTIAL PROPERTIES FOR EMERGENCY DETECTION (CESSNA 172P)
    #------------------------------------------------------------------------------

    #--------------------------
    # ANNUNCIATORS (FG 2024.1+)
    #--------------------------
    class ANNUNCIATORS:
        MASTER_CAUTION = "/instrumentation/annunciators/master-caution/state"
        MASTER_WARNING = "/instrumentation/annunciators/master-warning/state"
        
        # Engine warnings
        ENGINE_FIRE = "/instrumentation/annunciators/engines/fire"
        OIL_PRESS_LOW = "/instrumentation/annunciators/engines/oil-pressure-low"
        FUEL_PRESS_LOW = "/instrumentation/annunciators/systems/fuel/pressure-low"
        VACUUM_FAIL = "/instrumentation/annunciators/systems/vacuum"
        
        # System warnings
        CARB_HEAT_ON = "/instrumentation/annunciators/systems/carb-heat"
        PITOT_HEAT_ON = "/instrumentation/annunciators/systems/pitot-heat"

    #--------------------------
    # FUEL SYSTEM
    #--------------------------
    class FUEL:
        LEFT_QTY_GAL = "/consumables/fuel/tank[0]/level-gal_us"
        RIGHT_QTY_GAL = "/consumables/fuel/tank[1]/level-gal_us"
        TOTAL_GAL = "/consumables/fuel/total-gal_us"
        DENSITY_PPG = "/consumables/fuel/tank[0]/density-ppg"
        
        # Controls
        SELECTOR = "/controls/fuel/tank[0]/fuel_selector"  # 0=OFF, 1=LEFT, 2=RIGHT, 3=BOTH
        PUMP = "/controls/engines/engine[0]/fuel-pump"

    #--------------------------
    # ENGINE SYSTEMS
    #--------------------------
    class ENGINE:
        # Status
        RPM = "/engines/engine[0]/rpm"
        EGT_F = "/engines/engine[0]/egt-degf"
        CHT_F = "/engines/engine[0]/cht-degf"
        OIL_TEMP_F = "/engines/engine[0]/oil-temperature-degf"
        OIL_PRESS_PSI = "/engines/engine[0]/oil-pressure-psi"
        FUEL_FLOW_GPH = "/engines/engine[0]/fuel-flow-gph"
        RUNNING = "/engines/engine[0]/running"
        
        # Controls
        THROTTLE = "/controls/engines/engine[0]/throttle"
        MIXTURE = "/controls/engines/engine[0]/mixture"
        CARB_HEAT = "/controls/anti-ice/engine[0]/carb-heat"  # 0=OFF, 1=ON
        MAGNETOS = "/controls/engines/engine[0]/magnetos"  # 0=OFF, 1=R, 2=L, 3=BOTH

    #--------------------------
    # FLIGHT CONTROLS
    #--------------------------
    class CONTROLS:
        AILERON = "/controls/flight/aileron"
        ELEVATOR = "/controls/flight/elevator"
        RUDDER = "/controls/flight/rudder"
        ELEVATOR_TRIM = "/controls/flight/elevator-trim"
        FLAPS = "/controls/flight/flaps"  # 0=UP, 0.33=10°, 0.66=20°, 1.0=FULL
        BRAKES = "/controls/gear/brake-left"  # 0=OFF, 1=ON

    #--------------------------
    # ENVIRONMENTAL
    #--------------------------
    class ENVIRONMENT:
        OAT_C = "/environment/temperature-degc"
        OAT_F = "/environment/temperature-degf"
        HUMIDITY = "/environment/relative-humidity"
        VISIBILITY = "/environment/visibility-m"
        WIND_SPEED = "/environment/wind-speed-kt"

    #--------------------------
    # FLIGHT STATE
    #--------------------------
    class FLIGHT:
        # Position
        LATITUDE = "/position/latitude-deg"
        LONGITUDE = "/position/longitude-deg"
        ALTITUDE_FT = "/position/altitude-ft"
        ALTITUDE_AGL_FT = "/position/altitude-agl-ft"
        
        # Attitude
        PITCH_DEG = "/orientation/pitch-deg"
        ROLL_DEG = "/orientation/roll-deg"
        HEADING_DEG = "/orientation/heading-deg"
        
        # Motion
        AIRSPEED_KT = "/velocities/airspeed-kt"
        VERTICAL_SPEED_FPS = "/velocities/vertical-speed-fps"
        ACCEL_Z = "/accelerations/pilot/z-accel-fps_sec"  # For stall detection

    #--------------------------
    # ELECTRICAL SYSTEM
    #--------------------------
    class ELECTRICAL:
        BATTERY_VOLTS = "/systems/electrical/outputs/battery/voltage-v"
        ALTERNATOR_AMPS = "/systems/electrical/outputs/alternator/current-a"
        BUS_VOLTS = "/systems/electrical/outputs/bus/voltage-v"

    #--------------------------
    # SIMULATION CONTROL
    #--------------------------
    SIM_SPEEDUP = "/sim/speedup"