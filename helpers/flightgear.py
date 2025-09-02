# helpers/flightgear.py
import logging
import time
import queue
import shutil
import joblib
import os
import sys

# --- Path Correction ---
HELPER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HELPER_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Core Project Imports ---
from shallnotcrash.fg_interface.protocols.telnet import TelnetProtocol
from shallnotcrash.constants.connection import FGConnectionConstants
from shallnotcrash.constants.flightgear import FGProps
# [MODIFIED] Import the AnomalyDetector CLASS, not the removed global singleton.
from shallnotcrash.emergency.analyzers.anomaly_detector import AnomalyDetector, FlightPhase
from shallnotcrash.emergency.analyzers.pattern_recognizer import PatternRecognizer

MODEL_PATH = os.path.join(PROJECT_ROOT, "models", "c172p_emergency_model_improved.joblib")

def find_fgfs_executable() -> str:
    for path in ['/usr/games/fgfs', '/usr/bin/fgfs', 'fgfs']:
        if shutil.which(path): return path
    return None

def try_connect_fg(state: dict):
    try:
        state['fg_interface'] = TelnetProtocol(host=FGConnectionConstants.DEFAULT_HOST, port=FGConnectionConstants.DEFAULT_PORT, timeout=2.0)
        state['fg_interface'].get(FGProps.FLIGHT.LATITUDE)
        state['fg_connected'] = True
    except Exception:
        state['fg_interface'], state['fg_connected'] = None, False

def get_prop(fg, prop, default=0.0):
    try:
        return fg.get(prop) or default
    except Exception:
        return default

def telemetry_worker(state: dict):
    try:
        emergency_model = joblib.load(MODEL_PATH)
        logging.info("Emergency detection model loaded successfully.")
    except Exception as e:
        logging.error(f"MODEL NOT FOUND at {MODEL_PATH}. Error: {e}")
        emergency_model = None

    # These will hold the private instances for the current connection.
    pattern_recognizer = None
    anomaly_detector = None 
    first_connection_established = False

    while True:
        try:
            data_packet = { 'timestamp': time.time() }

            if not state['fg_connected']:
                try_connect_fg(state)

            if state['fg_connected'] and state['fg_interface']:
                if not first_connection_established:
                    logging.info("FlightGear connection established. Initializing fresh detection system.")
                    # Create NEW, PRIVATE instances of the recognizer and detector.
                    pattern_recognizer = PatternRecognizer(MODEL_PATH if emergency_model else None)
                    anomaly_detector = AnomalyDetector()
                    first_connection_established = True
                
                fg = state['fg_interface']
                raw_telemetry = {
                    'rpm': get_prop(fg, FGProps.ENGINE.RPM), 'oil_pressure': get_prop(fg, FGProps.ENGINE.OIL_PRESS_PSI),
                    'fuel_flow': get_prop(fg, FGProps.ENGINE.FUEL_FLOW_GPH), 'g_load': get_prop(fg, FGProps.FLIGHT.G_LOAD, default=1.0),
                    'vibration': get_prop(fg, FGProps.ENGINE.VIBRATION), 'bus_volts': get_prop(fg, FGProps.ELECTRICAL.BUS_VOLTS),
                    'oil_temp': get_prop(fg, FGProps.ENGINE.OIL_TEMP_F), 'cht': get_prop(fg, FGProps.ENGINE.CHT_F),
                    'egt': get_prop(fg, FGProps.ENGINE.EGT_F), 'control_asymmetry': 0.0,
                    'airspeed': get_prop(fg, FGProps.FLIGHT.AIRSPEED_KT),
                    'yaw_rate': get_prop(fg, FGProps.FLIGHT.YAW_RATE_DEGPS),
                    'roll': get_prop(fg, FGProps.FLIGHT.ROLL_DEG),
                    'pitch': get_prop(fg, FGProps.FLIGHT.PITCH_DEG)
                }
                data_packet.update({
                    'lat': get_prop(fg, FGProps.FLIGHT.LATITUDE), 'lng': get_prop(fg, FGProps.FLIGHT.LONGITUDE),
                    'heading': get_prop(fg, FGProps.FLIGHT.HEADING_DEG), 'speed': raw_telemetry['airspeed'],
                    'altitude': get_prop(fg, FGProps.FLIGHT.ALTITUDE_FT), 'fg_connected': True, 'raw_telemetry': raw_telemetry
                })

                if pattern_recognizer and anomaly_detector:
                    elapsed = time.time() - pattern_recognizer.startup_time
                    grace_is_active = elapsed < pattern_recognizer.STARTUP_GRACE_PERIOD

                    if grace_is_active:
                        data_packet['emergency_result'] = {'pattern_type': 'GRACE_PERIOD'}
                        data_packet['anomaly_scores'] = {k: 0.0 for k in raw_telemetry.keys()}
                        data_packet['system_status'] = {'grace_period_remaining': pattern_recognizer.STARTUP_GRACE_PERIOD - elapsed}
                    else:
                        # Use the private, clean anomaly_detector instance.
                        scores = anomaly_detector.detect(raw_telemetry, FlightPhase.CRUISE)
                        result = pattern_recognizer.predict_pattern(raw_telemetry, scores)
                        
                        if result:
                            pattern_type = result.pattern_type.value if hasattr(result.pattern_type, 'value') else str(result.pattern_type)
                            if pattern_type == 'UNKNOWN': pattern_type = 'NORMAL'
                            data_packet['emergency_result'] = {'pattern_type': pattern_type, 'probability': result.probability}
                        else:
                            data_packet['emergency_result'] = {'pattern_type': 'NORMAL', 'probability': 1.0}

                        data_packet['anomaly_scores'] = {k: v.normalized_score for k, v in scores.items()}
                        data_packet['system_status'] = {'grace_period_remaining': 0}
                else:
                    data_packet.update({'emergency_result': {'pattern_type': 'NO_MODEL'}, 'anomaly_scores': {}, 'system_status': {}})
            
            else: 
                data_packet.update({'fg_connected': False, 'emergency_result': {'pattern_type': 'DISCONNECTED'},
                                    'raw_telemetry': {}, 'anomaly_scores': {}, 'system_status': {}})
                if first_connection_established:
                    logging.info("FG disconnected. Clearing detection state.")
                first_connection_established, pattern_recognizer, anomaly_detector = False, None, None
                time.sleep(1)

            try:
                state['telemetry_queue'].get_nowait()
            except queue.Empty:
                pass
            state['telemetry_queue'].put(data_packet)
            time.sleep(0.5)

        except Exception as e:
            logging.error(f"FATAL ERROR in telemetry_worker: {e}", exc_info=True)
            state['fg_connected'] = False
            first_connection_established, pattern_recognizer, anomaly_detector = False, None, None
            time.sleep(5)
            