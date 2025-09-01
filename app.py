# app.py
import logging
import threading
import subprocess
import queue
import os
import time
from flask import Flask, render_template, jsonify

from helpers.flightgear import find_fgfs_executable, try_connect_fg, telemetry_worker
from shallnotcrash.constants.connection import FGConnectionConstants

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# --- Global State Dictionary ---
state = {
    'fg_interface': None,
    'fg_connected': False,
    'telemetry_queue': queue.Queue(maxsize=1),
    'last_good_telemetry': {
        'lat': None, 'lng': None, 'heading': None, 'speed': None, 'altitude': None,
        'roll': None, 'pitch': None, 'yaw_rate': None,
        'fg_connected': False, 'emergency_result': {'pattern_type': 'NORMAL'}
    }
}

@app.route('/')
def index():
    return render_template('hud.html')

@app.route('/position')
def position():
    try:
        # Get the latest data packet from the worker thread
        data = state['telemetry_queue'].get_nowait()
        # Also update the fallback cache with this fresh data
        state['last_good_telemetry'] = data.copy()
    except queue.Empty:
        # If queue is empty, use the last known good data
        data = state['last_good_telemetry'].copy()
        # CRITICAL FIX: Always override the connection status in the fallback
        # with the real-time status from the global state.
        data['fg_connected'] = state['fg_connected']
    return jsonify(data)

@app.route('/start_fg', methods=['POST'])
def start_fg():
    fg_executable = find_fgfs_executable()
    if not fg_executable:
        error_msg = "'fgfs' executable not found. Please ensure FlightGear is installed."
        logging.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500
        
    start_lat, start_lon = 64.05, -22.5
    fg_command = [ fg_executable, "--airport=BIKF", "--aircraft=c172p", f"--lat={start_lat}", f"--lon={start_lon}",
                   "--heading=180", "--altitude=5000 --timeofday=noon",
                   f"--telnet=socket,bi,10,{FGConnectionConstants.DEFAULT_HOST},{FGConnectionConstants.DEFAULT_PORT},tcp" ]
    logging.info(f"Attempting to start FlightGear with command: {' '.join(fg_command)}")
    try:
        subprocess.Popen(fg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(15)
        try_connect_fg(state)
        return jsonify({'success': state['fg_connected']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    try_connect_fg(state)
    
    # [THE FIX] Correctly start the background thread, passing the state dictionary.
    # The 'project_root' argument was incorrect and has been removed.
    threading.Thread(target=telemetry_worker, args=(state,), daemon=True).start()
    
    app.run(debug=True, use_reloader=False)
    