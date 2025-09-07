#!/usr/bin/env python3
"""
[FINAL ANALYSIS BUILD - V13]
This version adds detailed printouts for every waypoint in a generated path,
allowing for full analytical review of the final, ultra-smooth trajectory.
"""
import sys
import math
from pathlib import Path
from typing import Dict
import plotly.graph_objects as go

sys.path.append(str(Path(__file__).resolve().parent.parent))

# --- MODULAR IMPORTS ---
from shallnotcrash.landing_site import LandingSiteFinder, SearchConfig
from shallnotcrash.landing_site.visualization import MapVisualizer
from shallnotcrash.path_planner import PathPlanner, FlightPath
from shallnotcrash.path_planner.data_models import AircraftState
from shallnotcrash.emergency.constants import EmergencySeverity

# --- HELPER FUNCTIONS ---
def _get_cardinal_direction(heading_deg: float) -> str:
    """Converts a heading in degrees to a cardinal direction string."""
    dirs = ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"]
    index = round(heading_deg / 45) % 8
    return dirs[index]

def _inject_simulated_elevation_data(search_results):
    for site in search_results.landing_sites:
        if not hasattr(site, 'elevation_m') or site.elevation_m is None or math.isnan(site.elevation_m):
            site.elevation_m = 50.0
    return search_results

# --- MISSION PARAMETERS ---
SCENARIO_NAME = "Live Integrated Emergency Response: BIKF"
AIRCRAFT_START_STATE = AircraftState(lat=64.05, lon=-22.58, alt_ft=5000.0, airspeed_kts=68.0, heading_deg=225.0)
SEARCH_LAT = 64.05; SEARCH_LON = -22.58

def run_full_system_test():
    """Executes the full mission with the fully encapsulated planner."""
    print("Commencing Full System Demo (Fully Encapsulated Planner).")
    
    initial_heading_cardinal = _get_cardinal_direction(AIRCRAFT_START_STATE.heading_deg)
    print(f"Aircraft Initial State: {AIRCRAFT_START_STATE.alt_ft} ft, Heading {AIRCRAFT_START_STATE.heading_deg}° ({initial_heading_cardinal})")

    print("\n[PHASE 1 & 2] Acquiring and enhancing landing sites...")
    config = SearchConfig(search_radius_km=20, max_sites_return=5)
    finder = LandingSiteFinder(config=config)
    search_results = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)
    if not search_results.landing_sites: print("\n! MISSION FAILURE: No sites found."); return
    search_results = _inject_simulated_elevation_data(search_results)
    print("Site acquisition complete.")

    print("\n[PHASE 3] Generating tactical glide paths...")
    planner = PathPlanner()
    all_flight_paths: Dict[int, FlightPath] = {}
    
    for i, site in enumerate(search_results.landing_sites):
        site_label = getattr(site, 'designator', f"{site.site_type.replace('_', ' ').title()} #{i+1}")
        print(f"  -> Planning for Option #{i+1} ({site_label})...")
        
        path = planner.generate_path(
            current_state=AIRCRAFT_START_STATE,
            target_site=site
        )
        
        print(f"Path {i}: ", path)

        if i == 0:
            break
        
if __name__ == "__main__":
    run_full_system_test()