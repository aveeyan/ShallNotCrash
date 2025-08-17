#!/usr/bin/env python3
"""
Full System Operational Demonstration for ShallNotCrash (v9 - Function-Based API).
This script is now corrected to use the function-based API from the touchdown
utility, aligning it with the final, simplified module design.
"""
import sys
from pathlib import Path
from typing import Dict
import plotly.graph_objects as go

sys.path.append(str(Path(__file__).resolve().parent.parent))

# --- MODULAR IMPORTS (CORRECTED) ---
from shallnotcrash.landing_site import LandingSiteFinder, SearchConfig
from shallnotcrash.landing_site.visualization import MapVisualizer
from shallnotcrash.path_planner import PathPlanner, FlightPath
from shallnotcrash.path_planner.data_models import AircraftState
# [FIXED] Import the 'touchdown' module itself to access its functions.
from shallnotcrash.path_planner.utils import touchdown
from shallnotcrash.emergency.constants import EmergencySeverity

# --- HELPER FUNCTIONS (UNCHANGED LOGIC, TYPO FIXED) ---
def _inject_simulated_elevation_data(search_results):
    for site in search_results.landing_sites:
        if not hasattr(site, 'elevation_m') or site.elevation_m is None: site.elevation_m = 50.0
    # [FIXED] Corrected a typo in the return variable name.
    return search_results

def _generate_3d_visualization(start_state, search_results, flight_paths) -> go.Figure:
    """Re-instated 3D plotting logic."""
    fig = go.Figure()
    fig.add_trace(go.Scatter3d(x=[start_state.lon], y=[start_state.lat], z=[start_state.alt_ft], mode='markers', marker=dict(size=10, color='green', symbol='circle'), name='Start Point'))
    for i, site in enumerate(search_results.landing_sites):
        if i not in flight_paths: continue
        path = flight_paths[i]
        site_label = getattr(site, 'designator', f"{site.site_type.replace('_', ' ').title()} #{i+1}")
        lons = [wp.lon for wp in path.waypoints]; lats = [wp.lat for wp in path.waypoints]; alts = [wp.alt_ft for wp in path.waypoints]
        fig.add_trace(go.Scatter3d(x=lons, y=lats, z=alts, mode='lines', line=dict(width=4), name=f'Path to {site_label}'))
        fig.add_trace(go.Scatter3d(x=[lons[-1]], y=[lats[-1]], z=[alts[-1]], mode='markers', marker=dict(size=8, color='red', symbol='cross'), name=f'Target: {site_label}'))
    fig.update_layout(title='3D Emergency Glide Path Visualization', scene=dict(xaxis_title='Longitude', yaxis_title='Latitude', zaxis_title='Altitude (ft MSL)', aspectratio=dict(x=1, y=1, z=0.5)), margin=dict(r=20, l=10, b=10, t=40))
    return fig

# --- MISSION PARAMETERS (UNCHANGED) ---
SCENARIO_NAME = "Live Integrated Emergency Response: BIKF"
AIRCRAFT_START_STATE = AircraftState(lat=64.05, lon=-22.58, alt_ft=3500.0, airspeed_kts=68.0, heading_deg=225.0)
SEARCH_LAT = 64.05; SEARCH_LON = -22.58
EMERGENCY_SCENARIO = EmergencySeverity.CRITICAL; WIND_CONDITION_DEG = 200.0

def run_full_system_test():
    """Executes the full mission with the modular planner and re-anchoring protocol."""
    print("Commencing Full System Demo (Function-Based API & Anchoring).")
    
    # === PHASE 1 & 2: SITE ACQUISITION ===
    print("\n[PHASE 1 & 2] Acquiring and enhancing landing sites...")
    config = SearchConfig(search_radius_km=20, max_sites_return=5)
    finder = LandingSiteFinder(config=config)
    search_results = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)
    if not search_results.landing_sites: print("\n! MISSION FAILURE: No sites found."); return
    search_results = _inject_simulated_elevation_data(search_results)
    print("Site acquisition complete.")

    # === PHASE 3: PATH GENERATION & HIGH-FIDELITY RE-ANCHORING ===
    print("\n[PHASE 3] Generating and anchoring tactical glide paths...")
    planner = PathPlanner()
    # [REMOVED] The TouchdownSelector class is no longer used.
    all_flight_paths: Dict[int, FlightPath] = {}

    for i, site in enumerate(search_results.landing_sites):
        print(f"  -> Planning for Option #{i+1} ({site.site_type.replace('_', ' ').title()})...")
        
        # --- [FIXED] CRITICAL PROTOCOL STEP 1: Determine the precise anchor point ---
        # We now call the get_landing_sequence function directly from the touchdown module.
        landing_sequence = touchdown.get_landing_sequence(site, WIND_CONDITION_DEG)
        if not landing_sequence:
            print(f"     ...Skipped: No valid landing sequence found for site {i+1}.")
            continue
        
        # The function returns (FAF, Threshold). The threshold is our anchor point.
        _faf_waypoint, anchor_waypoint = landing_sequence

        # --- Call the planner to get the smoothed path ---
        path = planner.generate_path(
            current_state=AIRCRAFT_START_STATE, target_site=site,
            emergency_type=EMERGENCY_SCENARIO.name, # Pass name of enum member
            wind_heading_deg=WIND_CONDITION_DEG
        )
        
        if path and path.waypoints:
            # --- CRITICAL PROTOCOL STEP 2: Re-anchor the smoothed path ---
            path.waypoints[0].lat = AIRCRAFT_START_STATE.lat
            path.waypoints[0].lon = AIRCRAFT_START_STATE.lon
            path.waypoints[0].alt_ft = AIRCRAFT_START_STATE.alt_ft # Also anchor start altitude
            
            path.waypoints[-1].lat = anchor_waypoint.lat
            path.waypoints[-1].lon = anchor_waypoint.lon
            path.waypoints[-1].alt_ft = anchor_waypoint.alt_ft

            print("     ...Path generated and re-anchored for precision.")
            all_flight_paths[i] = path
        else:
            print(f"     ...Path generation failed for site {i+1}.")

    if not all_flight_paths: print("\n! MISSION FAILURE: No paths could be generated."); return

    # === PHASE 4: FULL-SPECTRUM VISUALIZATION ===
    print("\n[PHASE 4] Generating 2D and 3D mission visualizations...")
    
    visualizer_2d = MapVisualizer()
    mission_map_2d = visualizer_2d.create_integrated_mission_map(
        start_state=AIRCRAFT_START_STATE, results=search_results, flight_paths=all_flight_paths
    )
    visualizer_2d.save_map(mission_map_2d, "mission_map_2d_integrated.html")
    print("-> 2D tactical map generated.")

    fig_3d = _generate_3d_visualization(AIRCRAFT_START_STATE, search_results, all_flight_paths)
    fig_3d.write_html("mission_map_3d_trajectory.html")
    print("-> 3D trajectory plot generated.")
    
    print(f"\n-> FULL SYSTEM MISSION SUCCESS: Review analysis files.")

if __name__ == "__main__":
    run_full_system_test()
    