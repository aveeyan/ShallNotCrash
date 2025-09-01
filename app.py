# app.py
import logging
import threading
import subprocess
import queue
import os
import time
import json
from flask import Flask, render_template, jsonify

from helpers.flightgear import find_fgfs_executable, try_connect_fg, telemetry_worker
from helpers.map_helpers import load_sites_as_geojson
from shallnotcrash.constants.connection import FGConnectionConstants

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

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
        data = state['telemetry_queue'].get_nowait()
        state['last_good_telemetry'] = data.copy()
    except queue.Empty:
        data = state['last_good_telemetry'].copy()
        data['fg_connected'] = state['fg_connected']
    return jsonify(data)

@app.route('/sites')
def find_sites():
    """
    Loads pre-cached landing sites as a GeoJSON FeatureCollection.
    The data transformation logic is handled by the load_sites_as_geojson helper.
    """
    cache_path = os.path.join(PROJECT_ROOT, "cache", "sites_cache.json")
    # This helper function now correctly formats the GeoJSON properties.
    sites_geojson = load_sites_as_geojson(cache_path)
    
    if not sites_geojson["features"]:
        return jsonify({'error': 'No sites with polygon data found in cache.'}), 404
        
    return jsonify(sites_geojson)


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
    
    threading.Thread(target=telemetry_worker, args=(state,), daemon=True).start()
    
    app.run(debug=True, use_reloader=False)
    