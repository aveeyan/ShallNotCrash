# app.py
import logging
import threading
import subprocess
import queue
import os
import time
import json
from flask import Flask, render_template, jsonify, request

# Core Application Imports
from helpers.flightgear import find_fgfs_executable, try_connect_fg, telemetry_worker
from helpers.map_helpers import load_sites_as_geojson, generate_realtime_path
from shallnotcrash.constants.connection import FGConnectionConstants

# Path Planning & Site Finding Imports
from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.data_models import LandingSite, SafetyReport

app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Global State Dictionary
state = {
    'fg_interface': None,
    'fg_connected': False,
    'telemetry_queue': queue.Queue(maxsize=1),
    'last_good_telemetry': { 'lat': 64.05, 'lng': -22.5, 'heading': 180.0, 'speed': 70.0, 'altitude': 5000.0, 'roll': 0, 'pitch': 0, 'yaw_rate': 0, 'fg_connected': False, 'emergency_result': {'pattern_type': 'NORMAL'}},
    'landing_sites_cache': []
}

@app.route('/')
def index():
    return render_template('hud.html')

@app.route('/position')
def position():
    try:
        data = state['telemetry_queue'].get_nowait()
        state['last_good_telemetry'].update(data)
    except queue.Empty:
        current_data = state['last_good_telemetry'].copy()
        current_data['fg_connected'] = state['fg_connected']
        return jsonify(current_data)
    return jsonify(state['last_good_telemetry'])

@app.route('/sites')
def find_sites():
    cache_path = os.path.join(PROJECT_ROOT, "cache", "sites_cache.json")
    if not os.path.exists(cache_path):
        return jsonify({'error': 'sites_cache.json not found!'}), 404
    try:
        with open(cache_path, 'r') as f:
            sites_as_dicts = json.load(f)
        state['landing_sites_cache'] = sites_as_dicts
        sites_geojson = load_sites_as_geojson(sites_as_dicts)
        logging.info(f"Successfully loaded {len(sites_as_dicts)} sites from cache.")
        return jsonify(sites_geojson)
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error processing cache file: {e}")
        return jsonify({'error': f'Could not process cache file: {e}'}), 500

@app.route('/plan_path', methods=['POST'])
def plan_path():
    data = request.json
    site_id = data.get('site_id')
    if site_id is None:
        return jsonify({'error': 'site_id is required.'}), 400

    terrain_analyzer = None
    try:
        logging.info("Initializing finder to get a valid terrain analyzer...")
        finder = LandingSiteFinder()
        current_lat = state['last_good_telemetry']['lat']
        current_lon = state['last_good_telemetry']['lng']
        dem_dir_path = os.path.join(PROJECT_ROOT, "shallnotcrash", "landing_site", "osm", "rasters")
        
        # [THE FIX] Call find_sites without the unsupported 'search_radius_km' argument.
        _ , terrain_analyzer = finder.find_sites(current_lat, current_lon, dem_dir_path)

        path_data = generate_realtime_path(
            terrain_analyzer=terrain_analyzer,
            sites_cache=state['landing_sites_cache'],
            telemetry=state['last_good_telemetry'],
            site_id=site_id
        )
        if path_data:
            return jsonify(path_data)
        else:
            return jsonify({'error': 'Path could not be generated for the selected site.'}), 500
            
    except Exception as e:
        logging.error(f"FATAL error in path planning: {e}", exc_info=True)
        return jsonify({'error': f'Path planning failed: {e}'}), 500
    finally:
        # The analyzer is created and destroyed within the 'try' block,
        # so we ensure its resources are released if it was successfully created.
        if terrain_analyzer and hasattr(terrain_analyzer, 'close_dem_sources'):
            terrain_analyzer.close_dem_sources()
            logging.info("Terrain analyzer resources have been released.")
            
@app.route('/start_fg', methods=['POST'])
def start_fg():
    fg_executable = find_fgfs_executable()
    if not fg_executable:
        error_msg = "'fgfs' executable not found. Please ensure FlightGear is installed."
        logging.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 500
    start_lat, start_lon = 64.05, -22.5
    fg_command = [ fg_executable, "--airport=BIKF", "--aircraft=c172p", f"--lat={start_lat}", f"--lon={start_lon}",
                   "--heading=180", "--altitude=5000", "--timeofday=noon",
                   f"--telnet=socket,bi,10,{FGConnectionConstants.DEFAULT_HOST},{FGConnectionConstants.DEFAULT_PORT},tcp" ]
    try:
        subprocess.Popen(fg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(15) # Give FG time to start up
        try_connect_fg(state)
        return jsonify({'success': state['fg_connected']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    try_connect_fg(state)
    # This is a placeholder for your actual telemetry worker
    # threading.Thread(target=telemetry_worker, args=(state,), daemon=True).start()
    app.run(debug=True, use_reloader=False)
