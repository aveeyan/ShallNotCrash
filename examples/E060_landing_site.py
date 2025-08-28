#!/usr/bin/env python3
"""
Operational Demonstration for the ShallNotCrash Landing Site Module.
Target Platform: Cessna 172P
Operational Area: Keflavík, Iceland (BIKF)
"""
import sys
import logging
from pathlib import Path
import time

# Ensure the root of the project is in the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from shallnotcrash.landing_site import LandingSiteFinder, SearchConfig
from shallnotcrash.landing_site.visualization import MapVisualizer

# --- Mission Parameters ---
SCENARIO_NAME = "Keflavík, Iceland (BIKF) - C172P Profile"
SEARCH_LAT = 63.9850
SEARCH_LON = -22.6056

def run_operational_test():
    """Executes the focused landing site detection mission."""
    print("Commencing Operational Demonstration for the Landing Site Module.")
    print(f"\n{'='*15} Scenario: {SCENARIO_NAME} {'='*15}")
    
    config = SearchConfig(search_radius_km=30, max_sites_return=15)
    finder = LandingSiteFinder(config=config)
    visualizer = MapVisualizer()
    
    print(f"\nSearching for sites suitable for a Cessna 172P...")
    start_time = time.time()
    
    # --- PROTOCOL CORRECTION ---
    # The 'aircraft_type' parameter is handled by the SearchConfig, not passed
    # directly into the find_sites method. The call has been corrected.
    results = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)
    
    processing_time = time.time() - start_time
    
    # --- Analyze and Report Findings ---
    if not results.landing_sites:
        print("\n! MISSION FAILURE: No viable landing sites were identified in the operational area.")
        if results.error:
            print(f"! System Advisory: {results.error}")
        return

    print(results)
    # --- Mission Success or Degraded Success ---
    print(f"\nSearch complete in {processing_time:.2f} seconds.")
    
    if results.error:
        print(f"\n! ADVISORY: {results.error}")
        print("! The following results are based on available local data only.")
    
    # --- ENHANCED REPORTING ---
    # The summary is now part of the SearchResults object and can be accessed directly.
    print("\n--- Top Landing Options ---")
    print(f"{'#':<3} {'Type':<18} {'Score':<7} {'Risk':<18} {'Dist (km)':<11} {'Dimensions (m)':<15} {'Surface'}")
    print('-'*95)
    for rank, site in enumerate(results.landing_sites, 1):
        dims = f"{site.length_m}x{site.width_m}"
        risk_report = f"{site.safety_report.risk_level} ({site.safety_report.safety_score})"
        print(f"{rank:<3} {site.site_type.replace('_', ' ').title():<18} {site.suitability_score:<7} {risk_report:<18} {site.distance_km:<11.2f} {dims:<15} {site.surface_type.title()}")
    
    print("\nGenerating interactive tactical map...")
    site_map = visualizer.create_map(results)
    map_filename = "map_bikf_c172p_demonstration.html"
    visualizer.save_map(site_map, map_filename)
    print(f"-> Mission map generated: '{map_filename}'. Open in a browser for review.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_operational_test()