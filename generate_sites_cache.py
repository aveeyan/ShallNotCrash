import os
import sys
import json
import logging
import math

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.path_planner.utils.touchdown import select_optimal_landing_approach
from shallnotcrash.path_planner.data_models import AircraftState

def haversine_distance_km(lat1, lon1, lat2, lon2):
    # ... (haversine function is unchanged) ...
    R = 6371.0
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# --- [NEW] Function to assign colors based on your rules ---
def assign_display_color(site: dict) -> str:
    """Assigns a hex color code based on risk level and site type."""
    safety_report = site.get('safety_report', {})
    
    # Priority 1: High-risk sites are always red
    if safety_report.get('risk_level', '').startswith('UNSAFE') or safety_report.get('risk_level') == 'HIGH':
        return '#8B0000' # Dark Red

    site_type = site.get('site_type', 'unknown').lower()

    # Priority 2: Color based on site type for safe sites
    if 'runway' in site_type:
        return '#00008B' # Dark Blue
    elif 'major_road' in site_type or 'motorway' in site_type:
        return '#1C1C1C' # Dark Black (Off-black)
    elif 'open_field' in site_type or 'grass' in site_type:
        return '#006400' # Dark Green
    
    # Default color for other safe sites (taxiways, etc.)
    return '#483D8B' # Dark Slate Blue

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    CACHE_DIR = "cache"
    CACHE_FILENAME = os.path.join(CACHE_DIR, "sites_cache.json")
    os.makedirs(CACHE_DIR, exist_ok=True)

    logging.info("--- Starting Advanced Landing Site Cache Generation ---")
    
    try:
        logging.info("[1] Initializing LandingSiteFinder...")
        finder = LandingSiteFinder()
        dem_dir_path = os.path.join(project_root, "shallnotcrash", "landing_site", "osm", "rasters")
        SEARCH_LAT, SEARCH_LON = 63.9850, -22.6056
        
        logging.info(f"[2] Finding all potential sites near ({SEARCH_LAT}, {SEARCH_LON})...")
        results_obj, analyzer = finder.find_sites(SEARCH_LAT, SEARCH_LON, dem_dir_path)
        logging.info(f"Found {len(results_obj.landing_sites)} raw sites.")
        
        logging.info("[3] Pre-computing optimal approach waypoints for each site...")
        final_sites = []
        dummy_state = AircraftState(lat=SEARCH_LAT, lon=SEARCH_LON, alt_ft=5000, heading_deg=180, airspeed_kts=70)
# generate_sites_cache.py (partial update)
# ... existing code ...

        for site in results_obj.landing_sites:
            site_dict = site.__dict__
            if 'safety_report' in site_dict and site_dict['safety_report']:
                site_dict['safety_report'] = site_dict['safety_report'].__dict__
            
            site_dict['display_color'] = assign_display_color(site_dict)

            # Calculate the best approach for this site
            approach_data = select_optimal_landing_approach(site, dummy_state)
            if approach_data:
                # [FIX] Handle both old and new return formats
                if len(approach_data) == 3:
                    # Old format: (faf, threshold, approach_heading)
                    faf_waypoint, threshold_waypoint, approach_hdg = approach_data
                    approach_waypoints = None
                else:
                    # New format: (faf, threshold, approach_heading, approach_waypoints)
                    faf_waypoint, threshold_waypoint, approach_hdg, approach_waypoints = approach_data
                
                # Store both individual waypoints and the full approach path
                site_dict['precomputed_faf'] = faf_waypoint.__dict__
                site_dict['precomputed_threshold'] = threshold_waypoint.__dict__
                site_dict['precomputed_approach_hdg'] = approach_hdg
                
                # Store the full approach waypoints if available
                if approach_waypoints:
                    site_dict['precomputed_approach_waypoints'] = [wp.__dict__ for wp in approach_waypoints]
                
                final_sites.append(site_dict)
            else:
                logging.warning(f"Could not compute approach for site at ({site.lat}, {site.lon}). Skipping.")

        # ... rest of the function ...
        analyzer.close_dem_sources()
        
        # Sort by suitability score as before
        sorted_sites = sorted(final_sites, key=lambda x: x.get('suitability_score', 0), reverse=True)
        
        with open(CACHE_FILENAME, 'w') as f:
            json.dump(sorted_sites, f, indent=2)

        logging.info(f"--- Successfully saved {len(sorted_sites)} sites with pre-computed approach data to {CACHE_FILENAME} ---")

    except Exception as e:
        logging.error(f"Cache generation failed: {e}", exc_info=True)
    
    import datetime

    # Add metadata to the cache
    cache_data = {
        'metadata': {
            'generated_at': datetime.datetime.now().isoformat(),
            'search_center': {'lat': SEARCH_LAT, 'lon': SEARCH_LON},
            'total_sites': len(sorted_sites),
            'sites_with_approaches': len([s for s in sorted_sites if 'precomputed_faf' in s])
        },
        'sites': sorted_sites
    }

    with open(CACHE_FILENAME, 'w') as f:
        json.dump(cache_data, f, indent=2)

    logging.info(f"--- Successfully saved {len(sorted_sites)} sites with metadata to {CACHE_FILENAME} ---")

if __name__ == "__main__":
    main()

