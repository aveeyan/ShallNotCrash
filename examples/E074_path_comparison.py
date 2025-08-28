# examples/E074_path_comparison.py
"""
[LIVE-FIRE SIMULATION]
Mission: E074 - Path Planner Judgment Validation

Objective: To verify that the integrated PathPlanner can distinguish between
a safe, viable flight path and an unsafe path over hazardous terrain.

This script serves as the final proof of concept before full system deployment.
"""
import logging
import sys
import os

# --- [SETUP] Ensure the core module is in the Python path ---
# This allows the example to be run directly from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState, Runway

def run_simulation():
    """Executes the full path comparison simulation."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [E074_SIM] - %(message)s')
    
    # --- [PHASE 1] Define Operational Parameters ---
    logging.info("Phase 1: Defining operational parameters and test scenarios.")

    # We will simulate the output of runway_loader.py with two strategic runways.
    # One is in a flat valley (SAFE), the other is deep in mountainous terrain (UNSAFE).
    runway_geneva_valley = Runway(
        name="LSGG RWY 22 (Safe Valley Approach)",
        start_lat=46.233, start_lon=6.09,
        end_lat=46.218, end_lon=6.11,
        center_lat=46.2255, center_lon=6.10,
        bearing_deg=224.0
    )
    
    runway_alpine_trap = Runway(
        name="LFXM RWY 18 (Unsafe Mountain Approach)",
        start_lat=45.85, start_lon=6.88, # Fictional runway near Mont Blanc
        end_lat=45.83, end_lon=6.88,
        center_lat=45.84, center_lon=6.88,
        bearing_deg=180.0
    )

    available_runways = [runway_geneva_valley, runway_alpine_trap]
    logging.info(f"Simulated runway data loaded. {len(available_runways)} runways available.")

    # --- [PHASE 2] Execute Scenario Alpha (Expected Success) ---
    logging.info("="*50)
    logging.info("Phase 2: Executing SCENARIO ALPHA - Safe Path Generation.")
    
    # This aircraft is north of Geneva, with a clear shot at the valley runway.
    aircraft_alpha = AircraftState(
        lat=46.4, lon=6.1, alt_ft=10000, airspeed_kts=150, heading_deg=180
    )
    logging.info(f"Aircraft Alpha State: Lat={aircraft_alpha.lat}, Lon={aircraft_alpha.lon}")

    # Instantiate the planner for this scenario.
    planner_alpha = PathPlanner(available_runways=[runway_geneva_valley])
    
    # Command the planner to generate and validate the path.
    validated_path_alpha = planner_alpha.generate_path(aircraft_alpha)

    # Report the verdict.
    if validated_path_alpha:
        logging.info("VERDICT: SUCCESS. Scenario Alpha path was generated and validated.")
        logging.info(f"Path Details: {validated_path_alpha.total_distance_nm:.2f} NM, {len(validated_path_alpha.waypoints)} waypoints.")
    else:
        logging.error("VERDICT: FAILURE. Scenario Alpha path was unexpectedly rejected.")
    
    # --- [PHASE 3] Execute Scenario Bravo (Expected Rejection) ---
    logging.info("="*50)
    logging.info("Phase 3: Executing SCENARIO BRAVO - Unsafe Path Rejection Test.")

    # This aircraft must plan a path directly over high mountain peaks to reach the trap runway.
    aircraft_bravo = AircraftState(
        lat=46.0, lon=6.88, alt_ft=12000, airspeed_kts=150, heading_deg=180
    )
    logging.info(f"Aircraft Bravo State: Lat={aircraft_bravo.lat}, Lon={aircraft_bravo.lon}")

    # Instantiate a new planner instance for clarity, targeting the unsafe runway.
    planner_bravo = PathPlanner(available_runways=[runway_alpine_trap])

    # Command the planner to generate and validate the path.
    validated_path_bravo = planner_bravo.generate_path(aircraft_bravo)

    # Report the verdict. The system's intelligence is proven by a rejection here.
    if not validated_path_bravo:
        logging.info("VERDICT: SUCCESS. Scenario Bravo path was correctly identified as unsafe and rejected.")
        logging.info("This demonstrates the TerrainAnalyzer is integrated and functional.")
    else:
        logging.error("VERDICT: CRITICAL FAILURE. Scenario Bravo path was approved. The system is blind.")
    logging.info("="*50)
    logging.info("Simulation Complete.")


if __name__ == "__main__":
    run_simulation()