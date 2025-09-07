#!/usr/bin/env python3
"""
[INTEGRATION SCRIPT - V4]
This script performs an end-to-end test of the ShallNotCrash system.

V4: Refactors imports to use the new public API of the 'path_planner'
package, eliminating deep, brittle imports and respecting encapsulation.
"""
import sys
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

sys.path.append(str(Path(__file__).resolve().parent.parent))

# --- [CRITICAL FIX] Use the clean, public API from the path_planner package ---
from shallnotcrash.path_planner import (
    PathPlanner,
    GuidanceComputer,
    AircraftState,
    Runway,
    Waypoint,
    FlightPath,
    get_midpoint,
    get_bearing
)

# Import the OSM network loader (its API is unchanged)
from shallnotcrash.landing_site.runway_loader import RunwayLoader

# --- Simulation Parameters ---
SIM_UPDATE_INTERVAL_MS = 100

# --- OSM Data Parser (Logic is unchanged, but it now uses the imported Runway object) ---
def parse_osm_data_to_runways(osm_data: list) -> list[Runway]:
    """
    Parses the raw JSON output from the Overpass API into a list of
    structured path_planner.data_models.Runway objects.
    """
    print("...Parsing raw OSM data into structured Runway objects.")
    runways = []
    nodes = {item['id']: (item['lat'], item['lon']) for item in osm_data if item['type'] == 'node'}
    
    for item in osm_data:
        if item['type'] == 'way' and item.get('tags', {}).get('aeroway') == 'runway':
            way_nodes = item.get('nodes', [])
            if len(way_nodes) < 2:
                continue

            start_node = nodes.get(way_nodes[0])
            end_node = nodes.get(way_nodes[-1])

            if not start_node or not end_node:
                continue
            
            tags = item.get('tags', {})
            runway_name = tags.get('ref', f"Runway_{item['id']}")
            midpoint = get_midpoint(start_node[0], start_node[1], end_node[0], end_node[1])
            bearing = get_bearing(start_node[0], start_node[1], end_node[0], end_node[1])
            length = float(tags.get('length', 0))
            width = float(tags.get('width', 0))
            surface = tags.get('surface', 'unknown')

            runways.append(Runway(
                name=runway_name,
                start_lat=start_node[0],
                start_lon=start_node[1],
                end_lat=end_node[0],
                end_lon=end_node[1],
                center_lat=midpoint[0],
                center_lon=midpoint[1],
                bearing_deg=bearing,
                length_m=length,
                width_m=width,
                surface_type=surface
            ))
    print(f"...Found and parsed {len(runways)} runways.")
    return runways


def run_integrated_simulation():
    """Executes the full planning and guidance loop."""
    print("--- PHASE 1: Generating Flight Plan (Slow Planner) ---")

    runway_loader = RunwayLoader()
    print("...Requesting runway data via network-based OSM loader.")
    raw_osm_data = runway_loader.get_runways(lat=63.985, lon=-22.605, radius_km=10)
    
    if not raw_osm_data:
        print("RunwayLoader returned no data. Check network or cache. Aborting.")
        return
        
    available_runways = parse_osm_data_to_runways(raw_osm_data)

    initial_aircraft_state = AircraftState(
        lat=64.05, lon=-22.58, alt_ft=5000.0, airspeed_kts=68.0, heading_deg=225.0
    )

    planner = PathPlanner(available_runways)
    full_flight_path = planner.generate_path(initial_aircraft_state)

    if not full_flight_path:
        print("Path planner failed to generate a path. Aborting simulation.")
        return

    print(f"Path generated successfully. Total waypoints: {len(full_flight_path.waypoints)}")
    print("-" * 50)

    print("--- PHASE 2: Initializing Guidance System ---")
    guidance_computer = GuidanceComputer()
    guidance_computer.load_new_path(full_flight_path)
    print("Guidance computer is live and using the generated flight plan.")
    print("-" * 50)

    print("--- PHASE 3: Commencing Real-Time Simulation Loop ---")
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_title("Integrated Guidance System (V4): Live View")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    path_lats = [wp.lat for wp in full_flight_path.waypoints]
    path_lons = [wp.lon for wp in full_flight_path.waypoints]

    ax.plot(path_lons, path_lats, 'k--', linewidth=1.0, label='Full Flight Path')
    aircraft_pos_plot, = ax.plot([], [], 'bo', markersize=10, label='Aircraft Position')
    target_wp_plot, = ax.plot([], [], 'r*', markersize=15, label='Current Target Waypoint')
    info_text = ax.text(0.02, 0.02, '', transform=ax.transAxes, fontsize=10,
                        verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax.legend()
    ax.grid(True)
    ax.axis('equal')

    def update(frame_index):
        current_waypoint = full_flight_path.waypoints[frame_index]
        current_aircraft_state = AircraftState(
            lat=current_waypoint.lat, lon=current_waypoint.lon, alt_ft=current_waypoint.alt_ft,
            airspeed_kts=current_waypoint.airspeed_kts, heading_deg=225.0
        )
        target_waypoint = guidance_computer.update_and_get_target(current_aircraft_state)
        aircraft_pos_plot.set_data([current_aircraft_state.lon], [current_aircraft_state.lat])
        if target_waypoint:
            target_wp_plot.set_data([target_waypoint.lon], [target_waypoint.lat])
            info = (
                f"Sim Step: {frame_index+1}/{len(full_flight_path.waypoints)}\n"
                f"Aircraft Alt: {current_aircraft_state.alt_ft:.0f} ft\n"
                f"Target WP Index: {guidance_computer.current_waypoint_index}\n"
                f"Target Alt: {target_waypoint.alt_ft:.0f} ft"
            )
            info_text.set_text(info)
        else:
            info_text.set_text("Final Waypoint Reached")
        return aircraft_pos_plot, target_wp_plot, info_text

    anim = FuncAnimation(
        fig, update, frames=len(full_flight_path.waypoints),
        interval=SIM_UPDATE_INTERVAL_MS, blit=True, repeat=False
    )
    plt.show()
    print("--- Simulation Complete ---")

if __name__ == "__main__":
    run_integrated_simulation()
