# helpers/flightgear.py
import logging
import time
import subprocess
import queue
import shutil
import joblib
import os

from shallnotcrash.fg_interface.protocols.telnet import TelnetProtocol
from shallnotcrash.constants.connection import FGConnectionConstants
from shallnotcrash.constants.flightgear import FGProps
from shallnotcrash.emergency.core import detect_emergency
# [MODIFIED] Import the ANOMALY_DETECTOR and the FlightPhase enum
from shallnotcrash.emergency.analyzers.anomaly_detector import ANOMALY_DETECTOR, FlightPhase

# [NEW] Determine the project root from this file's location
# This makes pathing to the model much more reliable.
HELPER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HELPER_DIR, '..'))


# --- [THE FIX] ---
# This patch corrects a state initialization issue in the AnomalyDetector
# without modifying its source file. It ensures the 'values' key exists for
# all pre-loaded baseline parameters. This code runs once when the module is imported.
try:
    unknown_phase_model = ANOMALY_DETECTOR.phase_models[FlightPhase.UNKNOWN]
    for param, model_data in unknown_phase_model.items():
        if 'values' not in model_data:
            model_data['values'] = []
    logging.info("Successfully patched AnomalyDetector's initial state.")
except Exception as e:
    logging.error(f"Failed to apply patch to AnomalyDetector: {e}")
# --- END FIX ---


def find_fgfs_executable() -> str:
    # ... (This function is unchanged)
    for path in ['/usr/games/fgfs', '/usr/bin/fgfs', 'fgfs']:
        if shutil.which(path):
            return path
    return None

def try_connect_fg(state: dict):
    # ... (This function is unchanged)
    try:
        state['fg_interface'] = TelnetProtocol(host=FGConnectionConstants.DEFAULT_HOST, port=FGConnectionConstants.DEFAULT_PORT, timeout=2.0)
        state['fg_interface'].get(FGProps.FLIGHT.LATITUDE)
        state['fg_connected'] = True
    except Exception:
        state['fg_interface'], state['fg_connected'] = None, False

def get_prop(fg, prop, default=0.0):
    # ... (This function is unchanged)
    try:
        return fg.get(prop)
    except Exception:
        return default

def telemetry_worker(state: dict):
    """Continuously polls FlightGear and runs the emergency detection pipeline."""
    model_path = os.path.join(PROJECT_ROOT, "models", "c172p_emergency_model_v3_tuned.joblib")
    emergency_model = joblib.load(model_path) if os.path.exists(model_path) else None
    if not emergency_model:
        logging.error(f"MODEL NOT FOUND at {model_path}. Emergency detection will be disabled.")

    while True:
        # ... (The rest of this function is correct and unchanged)
        data = state['last_good_telemetry'].copy()
        if state['fg_connected'] and state['fg_interface']:
            try:
                fg = state['fg_interface']
                raw_telemetry = {
                    'rpm': get_prop(fg, FGProps.ENGINE.RPM),
                    'oil_pressure': get_prop(fg, FGProps.ENGINE.OIL_PRESS_PSI),
                    'fuel_flow': get_prop(fg, FGProps.ENGINE.FUEL_FLOW_GPH),
                    'g_load': get_prop(fg, FGProps.FLIGHT.ACCEL_Z),
                    'vibration': get_prop(fg, FGProps.ENGINE.VIBRATION),
                    'bus_volts': get_prop(fg, FGProps.ELECTRICAL.BUS_VOLTS),
                    'control_asymmetry': 0.0
                }
                data.update({
                    'lat': get_prop(fg, FGProps.FLIGHT.LATITUDE), 'lng': get_prop(fg, FGProps.FLIGHT.LONGITUDE),
                    'heading': get_prop(fg, FGProps.FLIGHT.HEADING_DEG), 'speed': get_prop(fg, FGProps.FLIGHT.AIRSPEED_KT),
                    'altitude': get_prop(fg, FGProps.FLIGHT.ALTITUDE_FT), 'roll': get_prop(fg, FGProps.FLIGHT.ROLL_DEG),
                    'pitch': get_prop(fg, FGProps.FLIGHT.PITCH_DEG), 'yaw_rate': get_prop(fg, FGProps.FLIGHT.VERTICAL_SPEED_FPS)
                })
                data['fg_connected'] = True
                if emergency_model:
                    anomaly_scores = ANOMALY_DETECTOR.detect(raw_telemetry)
                    data['emergency_result'] = detect_emergency(raw_telemetry, anomaly_scores)
                state['last_good_telemetry'] = data.copy()
            except Exception as e:
                logging.error(f"Major telemetry read error: {e}")
                state['fg_connected'] = False
        else:
            data['fg_connected'] = False
            data['emergency_result'] = {'pattern_type': 'NORMAL'}
        try:
            state['telemetry_queue'].get_nowait()
        except queue.Empty: pass
        state['telemetry_queue'].put(data)
        time.sleep(0.2)
