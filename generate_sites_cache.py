import os
import sys
import json
import logging
import math

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from shallnotcrash.landing_site.core import LandingSiteFinder

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

    logging.info("--- Starting HYBRID Landing Site Cache Generation (with Colors) ---")
    
    all_sites = []
    
    try:
        logging.info("[1] Searching for sites using online methods...")
        finder = LandingSiteFinder()
        dem_dir_path = os.path.join(project_root, "shallnotcrash", "landing_site", "osm", "rasters")
        SEARCH_LAT, SEARCH_LON = 63.9850, -22.6056
        
        results_obj, analyzer = finder.find_sites(SEARCH_LAT, SEARCH_LON, dem_dir_path)
        analyzer.close_dem_sources()

        all_sites.extend([site.__dict__ for site in results_obj.landing_sites])
        logging.info(f"Found {len(results_obj.landing_sites)} sites via online methods.")
    except Exception as e:
        logging.warning(f"Online search failed: {e}. Check network or API status.")

    final_sites = []
    for site_dict in all_sites:
        if 'safety_report' in site_dict:
            site_dict['safety_report'] = site_dict['safety_report'].__dict__
        
        # --- [NEW] Assign the color before adding to the final list ---
        site_dict['display_color'] = assign_display_color(site_dict)
        final_sites.append(site_dict)

    sorted_sites = sorted(final_sites, key=lambda x: x.get('suitability_score', 0), reverse=True)
    
    with open(CACHE_FILENAME, 'w') as f:
        json.dump(sorted_sites, f, indent=2)

    logging.info(f"--- Successfully saved {len(sorted_sites)} sites with color data to {CACHE_FILENAME} ---")

if __name__ == "__main__":
    main()

