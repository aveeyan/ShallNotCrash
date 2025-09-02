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
        return jsonify({'error': 'sites_cache.json not found! Please run generate_sites_cache.py first.'}), 404
    
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
            
        # Handle both old and new cache formats
        if isinstance(cache_data, dict) and 'sites' in cache_data:
            # New format with metadata
            sites_as_dicts = cache_data['sites']
            metadata = cache_data.get('metadata', {})
            logging.info(f"Loaded {len(sites_as_dicts)} sites with metadata: {metadata}")
        elif isinstance(cache_data, list):
            # Old format - direct list
            sites_as_dicts = cache_data
            logging.info(f"Loaded {len(sites_as_dicts)} sites (legacy format)")
        else:
            return jsonify({'error': 'Invalid cache format. Expected list or dict with "sites" key.'}), 500
            
        # Update the global cache
        state['landing_sites_cache'] = sites_as_dicts
        
        # Convert to GeoJSON for the frontend
        sites_geojson = load_sites_as_geojson(sites_as_dicts)
        
        # Add some debug info
        response_data = sites_geojson.copy()
        response_data['debug'] = {
            'total_sites_loaded': len(sites_as_dicts),
            'cache_format': 'new' if isinstance(cache_data, dict) else 'legacy'
        }
        
        logging.info(f"Successfully loaded {len(sites_as_dicts)} sites from cache and converted to GeoJSON.")
        return jsonify(response_data)
        
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error processing cache file: {e}")
        return jsonify({'error': f'Could not process cache file: {e}'}), 500
    
@app.route('/plan_path', methods=['POST'])
def plan_path():
    data = request.json
    site_id = data.get('site_id')
    use_smart_caching = data.get('use_smart_caching', True)
    
    if site_id is None:
        return jsonify({'error': 'site_id is required.'}), 400

    # [FIX] Ensure sites cache is loaded
    if not state['landing_sites_cache']:
        cache_path = os.path.join(PROJECT_ROOT, "cache", "sites_cache.json")
        if not os.path.exists(cache_path):
            return jsonify({'error': 'sites_cache.json not found! Please run generate_sites_cache.py first.'}), 404
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
                
            # [FIX] Handle both old and new cache formats
            if isinstance(cache_data, dict) and 'sites' in cache_data:
                # New format with metadata
                state['landing_sites_cache'] = cache_data['sites']
                logging.info(f"Loaded {len(cache_data['sites'])} sites from cache with metadata.")
            elif isinstance(cache_data, list):
                # Old format - direct list
                state['landing_sites_cache'] = cache_data
                logging.info(f"Loaded {len(cache_data)} sites from cache (legacy format).")
            else:
                return jsonify({'error': 'Invalid cache format.'}), 500
                
        except (IOError, json.JSONDecodeError) as e:
            logging.error(f"Error loading cache: {e}")
            return jsonify({'error': f'Could not load cache: {e}'}), 500

    # [FIX] Validate site_id bounds
    if not isinstance(site_id, int) or site_id < 0 or site_id >= len(state['landing_sites_cache']):
        return jsonify({
            'error': f'Invalid site_id {site_id}. Valid range: 0-{len(state["landing_sites_cache"])-1}'
        }), 400

    terrain_analyzer = None
    try:
        logging.info(f"Planning path to site {site_id} (cache has {len(state['landing_sites_cache'])} sites)")
        finder = LandingSiteFinder()
        current_lat = state['last_good_telemetry']['lat']
        current_lon = state['last_good_telemetry']['lng']
        dem_dir_path = os.path.join(PROJECT_ROOT, "shallnotcrash", "landing_site", "osm", "rasters")
        
        _, terrain_analyzer = finder.find_sites(current_lat, current_lon, dem_dir_path)

        path_data = generate_realtime_path(
            terrain_analyzer=terrain_analyzer,
            sites_cache=state['landing_sites_cache'],
            telemetry=state['last_good_telemetry'],
            site_id=site_id,
            use_smart_caching=use_smart_caching
        )
        
        if path_data:
            logging.info(f"Successfully generated path with {len(path_data.get('waypoints', []))} waypoints")
            return jsonify(path_data)
        else:
            return jsonify({'error': 'Path could not be generated for the selected site.'}), 500
            
    except Exception as e:
        logging.error(f"FATAL error in path planning: {e}", exc_info=True)
        return jsonify({'error': f'Path planning failed: {e}'}), 500
    finally:
        if terrain_analyzer and hasattr(terrain_analyzer, 'close_dem_sources'):
            terrain_analyzer.close_dem_sources()
            logging.info("Terrain analyzer resources have been released.")

# Add this route to your app.py for debugging
@app.route('/debug/cache')
def debug_cache():
    """Debug endpoint to inspect cache status."""
    cache_path = os.path.join(PROJECT_ROOT, "cache", "sites_cache.json")
    
    debug_info = {
        'cache_file_exists': os.path.exists(cache_path),
        'cache_file_path': cache_path,
        'memory_cache_loaded': bool(state['landing_sites_cache']),
        'memory_cache_count': len(state['landing_sites_cache']) if state['landing_sites_cache'] else 0,
    }
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            if isinstance(cache_data, dict) and 'sites' in cache_data:
                debug_info.update({
                    'file_cache_format': 'new_with_metadata',
                    'file_cache_count': len(cache_data['sites']),
                    'file_cache_metadata': cache_data.get('metadata', {})
                })
            elif isinstance(cache_data, list):
                debug_info.update({
                    'file_cache_format': 'legacy_list',
                    'file_cache_count': len(cache_data)
                })
            
            # Show first few site IDs and types for debugging
            sites_list = cache_data['sites'] if isinstance(cache_data, dict) else cache_data
            debug_info['sample_sites'] = [
                {
                    'id': i,
                    'type': site.get('site_type', 'unknown'),
                    'lat': site.get('lat'),
                    'lon': site.get('lon'),
                    'has_precomputed': 'precomputed_faf' in site
                }
                for i, site in enumerate(sites_list[:5])  # First 5 sites
            ]
            
        except Exception as e:
            debug_info['file_cache_error'] = str(e)
    
    return jsonify(debug_info)

# [NEW] Add route to clear planner cache if needed
@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    try:
        from helpers.map_helpers import clear_planner_cache
        clear_planner_cache()
        return jsonify({'success': True, 'message': 'Planner cache cleared successfully.'})
    except Exception as e:
        logging.error(f"Error clearing cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
            
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
    threading.Thread(target=telemetry_worker, args=(state,), daemon=True).start()
    app.run(debug=True, use_reloader=False)
