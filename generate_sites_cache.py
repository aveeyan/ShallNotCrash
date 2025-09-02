# generate_sites_cache.py
import os
import sys
import json
import logging
import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.path_planner.utils.touchdown import select_optimal_landing_approach
from shallnotcrash.path_planner.data_models import AircraftState

def assign_display_color(site: dict) -> str:
    """Assigns a hex color code based on risk level and site type."""
    safety_report = site.get('safety_report', {})
    if safety_report.get('risk_level', '').startswith('UNSAFE') or safety_report.get('risk_level') == 'HIGH':
        return '#8B0000' # Dark Red
    site_type = site.get('site_type', 'unknown').lower()
    if 'runway' in site_type: return '#00008B' # Dark Blue
    elif 'major_road' in site_type or 'motorway' in site_type: return '#1C1C1C'
    elif 'open_field' in site_type or 'grass' in site_type: return '#006400'
    return '#483D8B'

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    CACHE_DIR = "cache"
    CACHE_FILENAME = os.path.join(CACHE_DIR, "sites_cache.json")
    os.makedirs(CACHE_DIR, exist_ok=True)

    logging.info("--- Starting Advanced Landing Site Cache Generation ---")
    
    finder = LandingSiteFinder()
    analyzer = None
    final_sites = []
    SEARCH_LAT, SEARCH_LON = 63.9850, -22.6056 # Search center (Keflavik Airport)
    
    try:
        dem_dir_path = os.path.join(project_root, "shallnotcrash", "landing_site", "osm", "rasters")
        logging.info(f"[1] Finding all potential sites near ({SEARCH_LAT}, {SEARCH_LON}). This may take a few minutes...")
        results_obj, analyzer = finder.find_sites(SEARCH_LAT, SEARCH_LON, dem_dir_path)
        
        if not results_obj or not results_obj.landing_sites:
            logging.warning("No landing sites found in the specified area.")
            return

        logging.info(f"[2] Found {len(results_obj.landing_sites)} raw sites. Processing elevation and approaches...")
        dummy_state = AircraftState(lat=SEARCH_LAT, lon=SEARCH_LON, alt_ft=5000, heading_deg=180, airspeed_kts=70)

        for site in results_obj.landing_sites:
            
            # [FIX] Get and assign the elevation for the site if it's missing.
            if site.elevation_m is None and analyzer:
                try:
                    elevation = analyzer.get_elevation_m(site.lat, site.lon)
                    if elevation is not None:
                        site.elevation_m = round(elevation, 2)
                except Exception as e:
                    logging.warning(f"Could not retrieve elevation for site at ({site.lat}, {site.lon}): {e}")
            
            site_dict = site.__dict__
            if hasattr(site.safety_report, '__dict__'):
                site_dict['safety_report'] = site.safety_report.__dict__
            
            site_dict['display_color'] = assign_display_color(site_dict)
            
            # Now that elevation is set, pre-computing the approach will be more accurate.
            approach_data = select_optimal_landing_approach(site, dummy_state)
            
            if approach_data:
                faf_waypoint, threshold_waypoint, approach_hdg, approach_waypoints = approach_data
                site_dict['precomputed_faf'] = faf_waypoint.__dict__ if faf_waypoint else None
                site_dict['precomputed_threshold'] = threshold_waypoint.__dict__ if threshold_waypoint else None
                site_dict['precomputed_approach_hdg'] = approach_hdg
                if approach_waypoints:
                    site_dict['precomputed_approach_waypoints'] = [wp.__dict__ for wp in approach_waypoints]
            
            final_sites.append(site_dict)

    except Exception as e:
        logging.error(f"Cache generation failed: {e}", exc_info=True)
    finally:
        if analyzer:
            analyzer.close_dem_sources()
            logging.info("Terrain analyzer resources released.")

    sorted_sites = sorted(final_sites, key=lambda x: (x.get('safety_report', {}).get('safety_score', 0)), reverse=True)
    
    cache_data = {
        'metadata': { 'generated_at': datetime.datetime.now().isoformat(), 'search_center': {'lat': SEARCH_LAT, 'lon': SEARCH_LON}, 'total_sites_found': len(sorted_sites) },
        'sites': sorted_sites
    }

    with open(CACHE_FILENAME, 'w') as f:
        json.dump(cache_data, f, indent=2)
    logging.info(f"--- Successfully saved {len(sorted_sites)} sites to {CACHE_FILENAME} ---")

if __name__ == "__main__":
    main()
    