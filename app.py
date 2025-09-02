# app.py
import logging
import threading
import subprocess
import queue
import os
import time
import json
from flask import Flask, render_template, jsonify, request
from pprint import pformat # [FIX] Added the missing import for the console debugger.

# Core Application Imports
from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.terrain_analyzer import TerrainAnalyzer
from helpers.flightgear import telemetry_worker, find_fgfs_executable
from helpers.map_helpers import load_sites_as_geojson, generate_realtime_path

# --- Global State Dictionary ---
state = {
    'fg_interface': None,
    'fg_connected': False,
    'telemetry_queue': queue.Queue(maxsize=1),
    'last_good_telemetry': {
        'lat': 64.05, 'lng': -22.5, 'heading': 180.0, 'speed': 70.0, 'altitude': 7500.0,
        'fg_connected': False,
        'emergency_result': {'pattern_type': 'INITIALIZING'},
        'anomaly_scores': {}, 'raw_telemetry': {}, 'system_status': {},
        'timestamp': time.time()
    },
    'landing_sites_cache': [],
    'terrain_analyzer': None 
}

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SITES_CACHE_PATH = os.path.join(PROJECT_ROOT, "cache", "sites_cache.json")

def get_or_create_terrain_analyzer() -> TerrainAnalyzer:
    """
    Initializes the TerrainAnalyzer on the first call and caches it in the global state.
    This version initializes the analyzer directly for elevation lookups, avoiding
    unnecessary network calls.
    """
    if state.get('terrain_analyzer') is None:
        logging.info("Initializing TerrainAnalyzer for elevation lookups...")
        try:
            dem_dir_path = os.path.join(PROJECT_ROOT, "shallnotcrash", "landing_site", "osm", "rasters")
            # Initialize directly, passing an empty list for obstacles as they are not needed for planning.
            analyzer = TerrainAnalyzer(all_nearby_elements=[], dem_dir_path=dem_dir_path)
            state['terrain_analyzer'] = analyzer
            logging.info("TerrainAnalyzer initialized and cached.")
        except Exception as e:
            logging.error(f"Failed to initialize TerrainAnalyzer: {e}", exc_info=True)
            return None
    return state['terrain_analyzer']

# --- Console Debugger ---
def console_debug_worker():
    """Prints the latest telemetry to the console for real-time debugging."""
    while True:
        try:
            data_to_print = state['last_good_telemetry'].copy()
            data_to_print.pop('raw_telemetry', None)
            data_to_print.pop('anomaly_scores', None)
            
            print("\n" + "="*50)
            print(f"DEBUG CONSOLE - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*50)
            print(pformat(data_to_print))
            print("="*50)

        except Exception as e:
            logging.error(f"Error in debug console: {e}")
        
        time.sleep(2.5)

# --- Site Finding and Path Planning ---
def load_sites_from_cache():
    if not state['landing_sites_cache']:
        if not os.path.exists(SITES_CACHE_PATH): return False, "sites_cache.json not found."
        try:
            with open(SITES_CACHE_PATH, 'r') as f:
                cache_data = json.load(f)
            sites_list = cache_data.get('sites', cache_data) if isinstance(cache_data, dict) else cache_data
            state['landing_sites_cache'] = sites_list
        except (IOError, json.JSONDecodeError): return False, "Could not process cache file."
    return True, "Cache loaded."

@app.route('/')
def index():
    return render_template('hud.html')

@app.route('/position')
def position():
    """Provides the latest, freshest telemetry data."""
    try:
        # [FIX] Wait up to 1 second for a new item from the worker.
        # This eliminates the data lag by ensuring the freshest data is always sent.
        data = state['telemetry_queue'].get(timeout=1.0)
        state['last_good_telemetry'].update(data)
        return jsonify(data)
    except queue.Empty:
        # If the worker is truly stopped/frozen, fallback to the last known data.
        return jsonify(state['last_good_telemetry'])

@app.route('/sites')
def find_sites_route():
    success, message = load_sites_from_cache()
    if not success: return jsonify({'error': message}), 500
    return jsonify(load_sites_as_geojson(state['landing_sites_cache']))
    
@app.route('/plan_path', methods=['POST'])
def plan_path():
    # --- THIS ROUTE IS REWRITTEN ---
    data = request.json
    site_id = data.get('site_id')
    
    if site_id is None: return jsonify({'error': 'site_id is required.'}), 400
    
    success, message = load_sites_from_cache()
    if not success: return jsonify({'error': message}), 500
    
    if not isinstance(site_id, int) or not (0 <= site_id < len(state['landing_sites_cache'])):
        return jsonify({'error': 'Invalid site_id.'}), 400
    
    # Get the cached analyzer instead of re-creating it
    terrain_analyzer = get_or_create_terrain_analyzer()
    if not terrain_analyzer:
        return jsonify({'error': 'Terrain analyzer could not be initialized.'}), 500
        
    try:
        # Pass the cached analyzer directly to the path generation function
        path_data = generate_realtime_path(
            terrain_analyzer, 
            state['landing_sites_cache'], 
            state['last_good_telemetry'], 
            site_id
        )
        return jsonify(path_data) if path_data else (jsonify({'error': 'Path could not be generated.'}), 500)
    except Exception as e:
        logging.error(f"Path planning error: {e}", exc_info=True)
        return jsonify({'error': 'Path planning failed.'}), 500
    # No finally block needed as we are not closing the analyzer anymore.
    #            
@app.route('/launch_fg', methods=['POST'])
def launch_fg():
    fg_executable = find_fgfs_executable()
    if not fg_executable: return jsonify({'success': False, 'error': "'fgfs' not found."}), 500
    from shallnotcrash.constants.connection import FGConnectionConstants
    fg_command = [fg_executable, "--airport=BIKF", "--aircraft=c172p", f"--lat={state['last_good_telemetry']['lat']}", f"--lon={state['last_good_telemetry']['lng']}", "--heading=180", "--altitude=5000", "--timeofday=noon", f"--telnet=socket,bi,10,{FGConnectionConstants.DEFAULT_HOST},{FGConnectionConstants.DEFAULT_PORT},tcp"]
    try:
        subprocess.Popen(fg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logging.info("FlightGear launch command issued.")
        return jsonify({'success': True, 'message': 'Launch command issued.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    threading.Thread(target=telemetry_worker, args=(state,), daemon=True).start()
    # threading.Thread(target=console_debug_worker, daemon=True).start()
    logging.info("Flask server starting. Open http://127.0.0.1:5000 in your browser.")
    app.run(debug=False, use_reloader=False)
    