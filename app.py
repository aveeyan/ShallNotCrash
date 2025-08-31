# app.py
import logging
import threading
import time
import subprocess
import queue
import shutil
import joblib
from flask import Flask, render_template, jsonify

# --- shallnotcrash Imports ---
from shallnotcrash.fg_interface.protocols.telnet import TelnetProtocol
from shallnotcrash.constants.connection import FGConnectionConstants
from shallnotcrash.constants.flightgear import FGProps

# [THE FIX] Import the superior, user-provided anomaly detector
from shallnotcrash.emergency.analyzers.anomaly_detector import ANOMALY_DETECTOR, detect_anomalies
from shallnotcrash.emergency.core import detect_emergency

app = Flask(__name__)

# --- Load the Emergency Pattern Recognition Model ---
MODEL_PATH = "shallnotcrash/emergency/models/c172p_emergency_model_v3_tuned.joblib"
EMERGENCY_MODEL = None
try:
    EMERGENCY_MODEL = joblib.load(MODEL_PATH)
    logging.info(f"Successfully loaded emergency detection model from {MODEL_PATH}")
except FileNotFoundError:
    logging.error(f"MODEL NOT FOUND at {MODEL_PATH}. Emergency detection will be disabled.")

# --- (Global state variables are unchanged) ---
fg_interface, fg_connected = None, False
telemetry_queue = queue.Queue(maxsize=1)
last_good_telemetry = {
    'lat': None, 'lng': None, 'heading': None, 'speed': None, 'altitude': None,
    'roll': None, 'pitch': None, 'fg_connected': False, 'emergency_pattern': 'NORMAL'
}

# --- (try_connect_fg is unchanged) ---
def try_connect_fg():
    global fg_interface, fg_connected
    # ... (code is unchanged)

def telemetry_worker():
    """Continuously polls FlightGear and runs the full emergency detection pipeline."""
    global fg_connected, last_good_telemetry
    while True:
        data = last_good_telemetry.copy()
        raw_telemetry = {}
        if fg_connected and fg_interface:
            try:
                # 1. Get all required telemetry from FlightGear
                raw_telemetry = {
                    'rpm': fg_interface.get(FGProps.ENGINE.RPM),
                    'oil_pressure': fg_interface.get(FGProps.ENGINE.OIL_PRESSURE_PSI),
                    'fuel_flow': fg_interface.get(FGProps.ENGINE.FUEL_FLOW_GPH),
                    'g_load': fg_interface.get(FGProps.ACCELERATION.G_NORM),
                    'vibration': fg_interface.get(FGProps.ENGINE.VIBRATION),
                    'bus_volts': fg_interface.get(FGProps.ELECTRICAL.BUS_VOLTS)
                    # Add any other parameters your anomaly_detector and model use
                }
                # Get non-emergency data separately
                data.update({
                    'lat': fg_interface.get(FGProps.FLIGHT.LATITUDE), 'lng': fg_interface.get(FGProps.FLIGHT.LONGITUDE),
                    'heading': fg_interface.get(FGProps.FLIGHT.HEADING_DEG), 'speed': fg_interface.get(FGProps.FLIGHT.AIRSPEED_KT),
                    'altitude': fg_interface.get(FGProps.FLIGHT.ALTITUDE_FT), 'roll': fg_interface.get(FGProps.FLIGHT.ROLL_DEG),
                    'pitch': fg_interface.get(FGProps.FLIGHT.PITCH_DEG)
                })
                data['fg_connected'] = True
                
                # 2. Run emergency detection if the model is loaded
                if EMERGENCY_MODEL:
                    # [THE FIX] Use your sophisticated anomaly detector
                    anomaly_scores = detect_anomalies(raw_telemetry)
                    emergency_result = detect_emergency(raw_telemetry, anomaly_scores)
                    data['emergency_pattern'] = emergency_result.get('pattern_type', 'NORMAL')
                
                last_good_telemetry = data.copy()
            except Exception:
                fg_connected = False
        else:
            data['fg_connected'] = False
            
        try:
            telemetry_queue.get_nowait()
        except queue.Empty: pass
        telemetry_queue.put(data)
        time.sleep(0.5)

# --- (The rest of the file is unchanged) ---
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)


@app.route('/')
def index():
    return render_template('hud.html')

@app.route('/position')
def position():
    try:
        data = telemetry_queue.get_nowait()
    except queue.Empty:
        data = last_good_telemetry.copy()
    return jsonify(data)

@app.route('/start_fg', methods=['POST'])
def start_fg():
    # [THE FIX] Use the helper function to find the fgfs command path
    fg_executable = find_fgfs_executable()
    if not fg_executable:
        error_msg = "'fgfs' executable not found in common paths. Please ensure FlightGear is installed."
        logging.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500
        
    start_lat, start_lon = 64.05, -22.5
    fg_command = [
        fg_executable,
        "--airport=BIKF", "--aircraft=c172p", f"--lat={start_lat}", f"--lon={start_lon}",
        "--heading=180", "--altitude=10000",
        f"--telnet=socket,bi,10,{FGConnectionConstants.DEFAULT_HOST},{FGConnectionConstants.DEFAULT_PORT},tcp"
    ]
    logging.info(f"Attempting to start FlightGear with command: {' '.join(fg_command)}")
    try:
        subprocess.Popen(fg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(15)
        try_connect_fg()
        return jsonify({'success': fg_connected, 'message': 'Connection successful' if fg_connected else 'Failed to connect after starting'})
    except Exception as e:
        logging.error(f"An unexpected error occurred while starting FlightGear: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    try_connect_fg()
    threading.Thread(target=telemetry_worker, daemon=True).start()
    app.run(debug=True, use_reloader=False)
