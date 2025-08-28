# examples/E075_ideal_path_validation.py
"""
[LIVE-FIRE SIMULATION]
Mission: E075 - Ideal Path Validation

Objective: To verify the system's ability to recognize and assign a maximum
or near-maximum safety score to a flight path over ideal, flat terrain.

This scenario serves as a calibration test for the safety scoring metric.
"""
import logging
import sys
import os

# --- [SETUP] Ensure the core module is in the Python path ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState, Runway

def run_ideal_condition_simulation():
    """Executes the ideal condition path validation."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [E075_SIM] - %(message)s')
    
    # --- [PHASE 1] Define Ideal Operational Parameters ---
    logging.info("="*50)
    logging.info("Phase 1: Defining SCENARIO CHARLIE - Ideal Conditions.")

    # Amsterdam Schiphol's "Polderbaan" runway is surrounded by exceptionally flat, low-lying land.
    runway_schiphol_flat = Runway(
        name="EHAM RWY 18R (Ideal Flat Approach)",
        start_lat=52.345, start_lon=4.72,
        end_lat=52.315, end_lon=4.72,
        center_lat=52.33, center_lon=4.72,
        bearing_deg=180.0
    )
    logging.info(f"Target runway defined: {runway_schiphol_flat.name}")

    # The aircraft is positioned north of the runway, over the flat coastal area / North Sea.
    # The path to the runway threshold is geometrically simple and over zero-elevation terrain.
    aircraft_charlie = AircraftState(
        lat=52.5, lon=4.72, alt_ft=5000, airspeed_kts=180, heading_deg=180
    )
    logging.info(f"Aircraft Charlie State: Lat={aircraft_charlie.lat}, Lon={aircraft_charlie.lon}")

    # --- [PHASE 2] Execute and Evaluate ---
    logging.info("Phase 2: Executing path generation and validation.")
    
    # Instantiate the planner with only the ideal runway.
    planner = PathPlanner(available_runways=[runway_schiphol_flat])
    
    # Command the planner to generate and validate the path.
    validated_path = planner.generate_path(aircraft_charlie)

    # --- [PHASE 3] Report Verdict ---
    logging.info("Phase 3: Reporting verdict.")
    if validated_path and validated_path.safety_report.safety_score > 95:
        logging.info("VERDICT: SUCCESS. Scenario Charlie path was validated with a near-perfect score.")
        logging.info(f"Path Details: {validated_path.total_distance_nm:.2f} NM")
        logging.info(f"Safety Report: is_safe={validated_path.safety_report.is_safe}, Score={validated_path.safety_report.safety_score}/100")
        logging.info("This confirms the scoring metric correctly identifies ideal conditions.")
    elif validated_path:
        logging.error("VERDICT: PARTIAL FAILURE. Path was approved but score was unexpectedly low.")
        logging.error(f"Safety Report: is_safe={validated_path.safety_report.is_safe}, Score={validated_path.safety_report.safety_score}/100")
    else:
        logging.error("VERDICT: CRITICAL FAILURE. Ideal path was incorrectly rejected.")
    
    logging.info("="*50)
    logging.info("Simulation Complete.")


if __name__ == "__main__":
    run_ideal_condition_simulation()
