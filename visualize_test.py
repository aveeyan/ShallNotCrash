# ~/Documents/shallnotcrash/visualize_test.py
import os
import sys
import logging

# --- Setup Python Path ---
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# --- Import Your Core Modules ---
from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.visualization import MapVisualizer
from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Generates an interactive map by finding all landing sites and pre-calculating
    the optimal flight path from a fixed starting point to each one.
    """
    print("--- Starting Interactive Path Visualization Test ---")

    # --- Configuration ---
    # Point A: Fixed aircraft starting position
    start_state = AircraftState(
        lat=64.05, lon=-22.5, alt_ft=5000.0,
        heading_deg=180.0, airspeed_kts=70.0
    )
    dem_dir_path = os.path.join(project_root, "shallnotcrash", "landing_site", "osm", "rasters")
    
    # --- Step 1: Find All Potential Landing Sites ---
    logging.info("Step 1: Finding all potential landing sites...")
    site_finder = LandingSiteFinder()
    site_results, terrain_analyzer = site_finder.find_sites(start_state.lat, start_state.lon, dem_dir_path)
    
    if not site_results.landing_sites:
        logging.error("No landing sites found. Cannot proceed.")
        return
    logging.info(f"Found {len(site_results.landing_sites)} total potential sites.")

    # --- Step 2: Pre-calculate a Path to EVERY Site ---
    logging.info("Step 2: Pre-calculating path for every site...")
    path_planner = PathPlanner(terrain_analyzer)
    flight_paths_dict = {}

    for i, site in enumerate(site_results.landing_sites):
        # Use the direct method to generate a path to this specific site
        flight_path = path_planner.generate_path_to_site(start_state, site)
        if flight_path:
            logging.info(f"  > Successfully planned path for site #{i+1}")
            flight_paths_dict[i] = flight_path
        else:
            logging.warning(f"  > FAILED to plan path for site #{i+1}")

    # --- Step 3: Visualize All Sites and All Paths ---
    logging.info("Step 3: Generating interactive visualization map...")
    visualizer = MapVisualizer()
    mission_map = visualizer.create_integrated_mission_map(
        start_state=start_state,
        results=site_results,
        flight_paths=flight_paths_dict
    )

    map_filename = "interactive_mission_map.html"
    mission_map.save(map_filename)
    
    logging.info(f"--- Test Complete ---")
    print(f"\nSuccess! Open '{map_filename}' in your browser to see the interactive results.")


if __name__ == "__main__":
    main()