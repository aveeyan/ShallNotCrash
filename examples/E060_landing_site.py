#!/usr/bin/env python3
"""
Operational Demonstration for the ShallNotCrash Landing Site Module (V2 Core).
Target Platform: Cessna 172P
Operational Area: Keflavík, Iceland (BIKF)

NOTE: This script is designed for the V2 architecture as defined in core.py.
It finds landing sites from OSM data and FlightGear runways.
"""
import sys
import logging
from pathlib import Path
import time

# Ensure the root of the project is in the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import the V2 modules
from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.data_models import SearchResults, SearchConfig

# --- Mission Parameters ---
SCENARIO_NAME = "Keflavík, Iceland (BIKF) - C172P Profile"
SEARCH_LAT = 63.9850  # Approximate Keflavik International Airport (BIKF)
SEARCH_LON = -22.6056
SEARCH_RADIUS_KM = 30  # Search a 30km radius from BIKF

def run_operational_test():
    """Executes the focused landing site detection mission using the V2 core."""
    print("Commencing Operational Demonstration for the Landing Site Module (V2).")
    print(f"\n{'='*15} Scenario: {SCENARIO_NAME} {'='*15}")
    
    # Initialize the finder with custom config
    config = SearchConfig(search_radius_km=SEARCH_RADIUS_KM)
    finder = LandingSiteFinder(config)
    
    print(f"\nSearching for landing sites near BIKF (Radius: {SEARCH_RADIUS_KM}km)...")
    start_time = time.time()
    
    # The V2 core's find_sites method returns SearchResults
    search_results: SearchResults = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)
    
    processing_time = time.time() - start_time
    
    # --- Analyze and Report Findings ---
    if not search_results.landing_sites:
        print("\n! MISSION FAILURE: No potential landing sites were identified in the operational area.")
        return

    print(f"\nSearch complete in {processing_time:.2f} seconds.")
    print(f"Found {len(search_results.landing_sites)} potential landing sites.")
    
    # --- ENHANCED REPORTING ---
    print("\n--- Identified Landing Sites ---")
    print(f"{'#':<3} {'Type':<12} {'Coordinates':<25} {'Orientation':<11} {'Dimensions (m)':<15} {'Surface':<12} {'Score':<6} {'Distance'}")
    print('-'*100)
    
    for rank, site in enumerate(search_results.landing_sites, 1):
        coords_str = f"({site.lat:.4f}, {site.lon:.4f})"
        orientation_str = f"{site.orientation_degrees:.1f}°" if site.orientation_degrees else "N/A"
        dims = f"{site.length_m:.0f}x{site.width_m:.0f}"
        surface = site.surface_type[:11] if site.surface_type else "Unknown"
        score = f"{site.suitability_score}/100"
        distance = f"{site.distance_km:.1f}km"
        
        print(f"{rank:<3} {site.site_type:<12} {coords_str:<25} {orientation_str:<11} {dims:<15} {surface:<12} {score:<6} {distance}")

    # --- Safety Analysis Summary ---
    safe_sites = [s for s in search_results.landing_sites if s.safety_report.is_safe]
    print(f"\nSafety Analysis:")
    print(f"  Safe sites: {len(safe_sites)}/{len(search_results.landing_sites)}")
    
    if search_results.landing_sites:
        avg_safety_score = sum(s.safety_report.safety_score for s in search_results.landing_sites) / len(search_results.landing_sites)
        print(f"  Average safety score: {avg_safety_score:.1f}/100")
        
        total_obstacles = sum(s.safety_report.obstacle_count for s in search_results.landing_sites)
        print(f"  Total obstacles detected: {total_obstacles}")

    # --- Save results for later inspection ---
    print(f"\nDetailed site data saved to 'bikf_landing_sites_report.txt'")
    with open('bikf_landing_sites_report.txt', 'w') as f:
        f.write(f"Landing Site Report for {SCENARIO_NAME}\n")
        f.write(f"Search Center: ({SEARCH_LAT}, {SEARCH_LON}), Radius: {SEARCH_RADIUS_KM}km\n")
        f.write(f"Generated at: {time.ctime()}\n")
        f.write(f"Processing time: {processing_time:.2f} seconds\n")
        f.write("="*80 + "\n\n")
        
        f.write("SEARCH PARAMETERS:\n")
        for key, value in search_results.search_parameters.items():
            f.write(f"  {key}: {value}\n")
        f.write("\n")
        
        f.write("LANDING SITES:\n")
        for i, site in enumerate(search_results.landing_sites, 1):
            f.write(f"\n{i}. {site.site_type.upper()}\n")
            f.write(f"   Location: ({site.lat:.6f}, {site.lon:.6f})\n")
            f.write(f"   Dimensions: {site.length_m:.0f}m x {site.width_m:.0f}m\n")
            f.write(f"   Orientation: {site.orientation_degrees:.1f}°\n")
            f.write(f"   Surface: {site.surface_type}\n")
            f.write(f"   Distance from origin: {site.distance_km:.2f}km\n")
            f.write(f"   Suitability score: {site.suitability_score}/100\n")
            
            # Safety details
            safety = site.safety_report
            f.write(f"   Safety status: {'SAFE' if safety.is_safe else 'UNSAFE'}\n")
            f.write(f"   Risk level: {safety.risk_level}\n")
            f.write(f"   Safety score: {safety.safety_score}/100\n")
            f.write(f"   Obstacles detected: {safety.obstacle_count}\n")
            f.write(f"   Closest civilian area: {safety.closest_civilian_distance_km:.2f}km\n")
            
            if safety.civilian_violations:
                f.write(f"   Civilian violations: {len(safety.civilian_violations)}\n")
            
            if site.elevation_m is not None:
                f.write(f"   Elevation: {site.elevation_m}m\n")
            
            # Polygon coordinates (simplified for readability)
            if site.polygon_coords and len(site.polygon_coords) > 0:
                f.write(f"   Polygon points: {len(site.polygon_coords)} coordinates\n")

    print("\nDemonstration complete. Use the report file for further analysis.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_operational_test()
