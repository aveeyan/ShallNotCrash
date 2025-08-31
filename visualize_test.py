# ~/Documents/shallnotcrash/visualize_test.py
import os
import sys
import logging

# --- Setup Python Path ---
# This ensures the script can find your 'shallnotcrash' package
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# --- Import Your Core Modules ---
from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.visualization import MapVisualizer
from shallnotcrash.landing_site.terrain_analyzer import TerrainAnalyzer
from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState

# --- Basic Logging Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    An end-to-end test script that finds landing sites, plans a path to the best one,
    and visualizes everything on an interactive map.
    """
    print("--- Starting End-to-End Visualization Test ---")

    # --- Configuration ---
    # BIKF Keflavik Airport Coordinates
    SEARCH_LAT, SEARCH_LON = 63.9850, -22.6056
    
    # Starting state of the aircraft (e.g., 10,000 ft, heading North)
    start_state = AircraftState(
        lat=SEARCH_LAT,
        lon=SEARCH_LON,
        alt_ft=10000.0,
        heading_deg=0.0,
        airspeed_kts=90.0
    )

    # Path to your offline Digital Elevation Model (DEM) files
    dem_dir_path = os.path.join(project_root, "shallnotcrash", "landing_site", "osm", "rasters")
    
    # --- Step 1: Find All Potential Landing Sites ---
    logging.info("Step 1: Finding all potential landing sites...")
    site_finder = LandingSiteFinder()
    
    # [THE FIX] Capture both the results and the analyzer from the find_sites function
    site_results, terrain_analyzer_for_planner = site_finder.find_sites(
        start_state.lat, start_state.lon, dem_dir_path
    )
    
    # ... (check for empty site_results is the same) ...
    if not site_results.landing_sites:
        logging.error("No landing sites found. Cannot proceed.")
        return
    logging.info(f"Found {len(site_results.landing_sites)} total potential sites.")

    # --- Step 2: Plan a Path to the Best Site ---
    logging.info("Step 2: Planning path to the optimal site...")
    
    # [THE FIX] The incorrect line is removed, as we now have the analyzer directly.
    path_planner = PathPlanner(terrain_analyzer_for_planner)
    
    optimal_flight_path = path_planner.find_best_path(start_state, site_results.landing_sites)

    # ... (The rest of the script is correct and remains the same) ...
    # --- Step 3: Visualize the Results ---
    logging.info("Step 3: Generating visualization map...")
    visualizer = MapVisualizer()
    flight_paths_dict = {}
    if optimal_flight_path:
        logging.info(f"Optimal path found with {len(optimal_flight_path.waypoints)} waypoints.")
        flight_paths_dict[0] = optimal_flight_path
    else:
        logging.warning("No optimal flight path could be generated.")
    mission_map = visualizer.create_integrated_mission_map(
        start_state=start_state,
        results=site_results,
        flight_paths=flight_paths_dict
    )
    map_filename = "mission_map.html"
    mission_map.save(map_filename)
    logging.info(f"--- Test Complete ---")
    logging.info(f"Interactive map saved to: {os.path.abspath(map_filename)}")
    print(f"\nSuccess! Open '{map_filename}' in your browser to see the results.")

if __name__ == "__main__":
    main()
