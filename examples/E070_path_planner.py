#!/usr/bin/env python3
"""
Full System Operational Demonstration for ShallNotCrash (v4 - Corrected Data Enhancement).
"""
import sys
from pathlib import Path
import time
from typing import Dict

# --- System-level Imports ---
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shallnotcrash.landing_site import LandingSiteFinder, SearchConfig
from shallnotcrash.path_planner import PathPlanner, FlightPath
from shallnotcrash.path_planner.data_models import AircraftState
from shallnotcrash.path_planner.visualization import PathVisualizer
from shallnotcrash.path_planner.utils.coordinates import destination_point
from shallnotcrash.emergency.constants import EmergencySeverity

# --- Tactical Data Enhancement Protocols ---

def _calculate_rectangular_polygon(site) -> list:
    """
    Calculates the four corners of a rectangular site (runway or taxiway).
    """
    # This function requires bearing, length, and width to be present.
    if not all(hasattr(site, attr) for attr in ['bearing_deg', 'length_m', 'width_m']):
        return []

    length_nm = site.length_m / 1852.0
    width_nm = site.width_m / 1852.0
    
    # Use the primary touchdown point as the reference for the polygon start
    p1 = (site.lat, site.lon)
    p4 = destination_point(site.lat, site.lon, site.bearing_deg, length_nm)
    
    # Calculate the four corners based on the runway centerline
    c1 = destination_point(p1[0], p1[1], site.bearing_deg - 90, width_nm / 2)
    c2 = destination_point(p1[0], p1[1], site.bearing_deg + 90, width_nm / 2)
    c3 = destination_point(p4[0], p4[1], site.bearing_deg + 90, width_nm / 2)
    c4 = destination_point(p4[0], p4[1], site.bearing_deg - 90, width_nm / 2)
    
    return [c1, c2, c3, c4, c1]

def _inject_simulated_elevation_data(search_results):
    for site in search_results.landing_sites:
        if not hasattr(site, 'elevation_m') or site.elevation_m is None:
            site.elevation_m = 50.0
    return search_results

# --- [Mission Parameters remain unchanged] ---
SCENARIO_NAME = "Live Integrated Emergency Response: BIKF"
AIRCRAFT_START_STATE = AircraftState(lat=64.05, lon=-22.58, alt_ft=3500.0, airspeed_kts=68.0, heading_deg=225.0)
SEARCH_LAT = 64.05
SEARCH_LON = -22.58
EMERGENCY_SCENARIO = EmergencySeverity.CRITICAL
WIND_CONDITION_DEG = 200.0

def run_full_system_test():
    """Executes the full, integrated mission with corrected data preparation."""
    print("Commencing Full System Operational Demonstration (Corrected).")
    print(f"\n{'='*15} Scenario: {SCENARIO_NAME} {'='*15}")

    # === PHASE 1 & 2: SITE ACQUISITION AND DATA ENHANCEMENT ===
    print("\n[PHASE 1 & 2] Acquiring and enhancing landing sites...")
    config = SearchConfig(search_radius_km=20, max_sites_return=5)
    finder = LandingSiteFinder(config=config)
    search_results = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)

    if not search_results.landing_sites:
        print("\n! MISSION FAILURE: No viable landing sites identified.")
        return
    
    search_results = _inject_simulated_elevation_data(search_results)
    
    # --- PATCH: Corrected and enhanced polygon generation logic ---
    print("INFO: Preparing high-fidelity polygons for visualization...")
    for site in search_results.landing_sites:
        # This protocol now correctly processes TAXIWAYs, which are being found
        # in place of RUNWAYs due to the missing apt.dat file.
        if site.site_type in ["RUNWAY", "TAXIWAY"]:
            site.polygon = _calculate_rectangular_polygon(site)
            if site.polygon:
                print(f"  -> Generated rectangular polygon for {site.site_type} at ({site.lat:.4f}, {site.lon:.4f})")
    # --- END PATCH ---
    
    print("Site acquisition and data enhancement complete.")

    # === PHASE 3: MULTI-TARGET PATH GENERATION ===
    print("\n[PHASE 3] Dispatching Path Planner for ALL viable targets...")
    planner = PathPlanner()
    all_flight_paths: Dict[int, FlightPath] = {}
    
    start_time = time.time()
    for i, site in enumerate(search_results.landing_sites):
        print(f"  -> Calculating path for Option #{i+1} ({site.site_type.replace('_', ' ').title()})...")
        path = planner.generate_path(
            current_state=AIRCRAFT_START_STATE,
            target_site=site,
            emergency_type=EMERGENCY_SCENARIO,
            wind_heading_deg=WIND_CONDITION_DEG
        )
        if path:
            all_flight_paths[i] = path
            print(f"     ...Path found ({len(path.waypoints)} waypoints).")
        else:
            print(f"     ...No viable path could be generated.")
            
    print(f"Path generation for all targets completed in {time.time() - start_time:.2f} seconds.")

    if not all_flight_paths:
        print("\n! MISSION FAILURE: Path Planner could not generate a path to ANY target.")
        return

    # === PHASE 4: ADVANCED VISUALIZATION ===
    print("\n[PHASE 4] Generating advanced mission analysis visualizations...")
    visualizer = PathVisualizer()
    map_2d = visualizer.create_multi_path_map(AIRCRAFT_START_STATE, search_results, all_flight_paths)
    visualizer.save_map(map_2d, "mission_map_interactive.html")
    fig_3d = visualizer.create_3d_plot(AIRCRAFT_START_STATE, search_results, all_flight_paths)
    visualizer.save_3d_plot(fig_3d, "mission_3d_visualization.html")
    print("\n-> FULL SYSTEM MISSION SUCCESS: Advanced analysis complete. Review HTML files.")

if __name__ == "__main__":
    run_full_system_test()