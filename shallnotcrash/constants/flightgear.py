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
        RPM = "/engines/engine/rpm"
        EGT_F = "/engines/engine/egt-degf"
        CHT_F = "/engines/engine/cht-degf"
        OIL_TEMP_F = "/engines/engine/oil-temperature-degf"
        OIL_PRESS_PSI = "/engines/engine/oil-pressure-psi"
        FUEL_FLOW_GPH = "/engines/engine/fuel-flow-gph"
        RUNNING = "/engines/engine/running"
        ## TODO: Find property tree or alternative to vibration
        VIBRATION = "/engines/engine/vibration"
        
        # Controls
        THROTTLE = "/controls/engines/engine/throttle"
        MIXTURE = "/controls/engines/engine/mixture"
        CARB_HEAT = "/controls/anti-ice/engine/carb-heat"  # 0=OFF, 1=ON
        MAGNETOS = "/controls/engines/engine/magnetos"  # 0=OFF, 1=R, 2=L, 3=BOTH

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
        AMBIENT_DENSITY = "/environment/density-slugft3"

    #--------------------------
    # FLIGHT STATE
    #--------------------------
    class FLIGHT:
        # Position
        LATITUDE = "/position/latitude-deg"
        LONGITUDE = "/position/longitude-deg"
        ALTITUDE_FT = "/position/altitude-ft"
        ALTITUDE_AGL_FT = "/position/altitude-agl-ft"
        GROUND_ELEV_FT = "/position/ground-elev-ft"
        
        # Attitude
        PITCH_DEG = "/orientation/pitch-deg"
        ROLL_DEG = "/orientation/roll-deg"
        HEADING_DEG = "/orientation/heading-deg"

        DOWN_RELGROUND_FPS ="/velocities/down-relground-fps"
        EAST_RELGROUND_FPS ="/velocities/east-relground-fps"
        NORTH_RELGROUND_FPS ="/velocities/north-relground-fps"
        
        SPEED_DOWN_FPS ="/velocities/speed-down-fps"
        SPEED_NORTH_FPS ="/velocities/speed-north-fps"
        SPEED_EAST_FPS ="/velocities/speed-east-fps"

        EQUIVALENT_KT = "/velocities/equivalent-kt"
        GROUNDSPEED_KT = "/velocities/groundspeed-kt"
        GLIDESLOPE = "/velocities/glideslope"
        MACH = "/velocities/mach"

        UBODY_FPS = "/velocities/uBody-fps"
        VBODY_FPS = "/velocities/vBody-fps"
        WBODY_FPS = "/velocities/wBody-fps"

        # Motion
        AIRSPEED_KT = "/velocities/airspeed-kt"
        VERTICAL_SPEED_FPS = "/velocities/vertical-speed-fps"
        ACCEL_Z = "/accelerations/pilot/z-accel-fps_sec"  # For stall detection

    #--------------------------
    # ELECTRICAL SYSTEM
    #--------------------------
    class ELECTRICAL:
        BATTERY_VOLTS = "/systems/electrical/volts"
        ALTERNATOR_AMPS = "/systems/electrical/amps"
        BUS_VOLTS = "/systems/electrical/volts"

    #--------------------------
    # SIMULATION CONTROL
    #--------------------------
    class SIMULATION:
        PAUSE = "/sim/freeze/master"
        FREEZE = PAUSE
        SIM_SPEEDUP = "/sim/speedup"

    class INSTRUMENTATION:
        ALTIMETER_HG = "/instrumentation/altimeter/setting-inhg"
