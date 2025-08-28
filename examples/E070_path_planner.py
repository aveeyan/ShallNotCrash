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

def _generate_3d_visualization(start_state, search_results, flight_paths) -> go.Figure:
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
        
        if path and path.waypoints:
            print(f"     ...Path generated successfully for {site_label}.")
            all_flight_paths[i] = path
            
            # # [ADDED] Print all waypoints for detailed analysis.
            # print(f"     ...Detailed Waypoints for {site_label}:")
            # for j, wp in enumerate(path.waypoints):
            #     print(f"       WP #{j+1}: Lat={wp.lat:.4f}, Lon={wp.lon:.4f}, Alt={wp.alt_ft:.0f} ft")
        else:
            print(f"     ...Path generation failed for site {site_label}.")

    if not all_flight_paths: print("\n! MISSION FAILURE: No paths could be generated."); return

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
