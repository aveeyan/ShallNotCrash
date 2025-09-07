#!/usr/bin/env python3
"""
Operational Demonstration for the ShallNotCrash Landing Site Module (V2 Core).
Target Platform: Cessna 172P
Operational Area: Keflavík, Iceland (BIKF)

UPDATED: Now uses current core.py and visualization.py modules with enhanced runway visualization.
"""
import sys
import logging
from pathlib import Path
import time

# Ensure the root of the project is in the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# Import the current modules
from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.data_models import SearchConfig
from shallnotcrash.landing_site.visualization import MapVisualizer

# --- Mission Parameters ---
SCENARIO_NAME = "Keflavík, Iceland (BIKF) - C172P Profile"
SEARCH_LAT = 63.9850  # Approximate Keflavik International Airport (BIKF)
SEARCH_LON = -22.6056
SEARCH_RADIUS_KM = 30  # Search a 30km radius from BIKF

def run_operational_test():
    """Executes the focused landing site detection mission using current modules."""
    print("Commencing Operational Demonstration for Landing Site Module (Current Version).")
    print(f"\n{'='*15} Scenario: {SCENARIO_NAME} {'='*15}")
    
    # Initialize the finder with custom config
    config = SearchConfig(
        search_radius_km=SEARCH_RADIUS_KM,
        max_sites_return=10,  # Limit to top 10 sites
        civilian_exclusion_radius_m=500,
        max_slope_degrees=2.0
    )
    finder = LandingSiteFinder(config)
    
    print(f"\nSearching for landing sites near BIKF (Radius: {SEARCH_RADIUS_KM}km)...")
    start_time = time.time()
    
    # The core's find_sites method returns SearchResults
    try:
        search_results = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)
        # Add this debugging code right after search_results = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)
        print("\n=== DEBUGGING SITE DATA ===")
        for i, site in enumerate(search_results.landing_sites[:3]):  # Check first 3 sites
            print(f"Site {i+1} ({site.site_type}):")
            print(f"  Location: ({site.lat}, {site.lon})")
            print(f"  Has polygon_coords attr: {hasattr(site, 'polygon_coords')}")
            if hasattr(site, 'polygon_coords'):
                print(f"  Polygon coords value: {site.polygon_coords}")
                print(f"  Polygon coords type: {type(site.polygon_coords)}")
                print(f"  Polygon coords length: {len(site.polygon_coords) if site.polygon_coords else 'None'}")
            print(f"  Orientation: {site.orientation_degrees}")
            print("---")
    except Exception as e:
        print(f"ERROR during site search: {e}")
        print("Check if all required data sources are available and configured properly.")
        return
    
    processing_time = time.time() - start_time
    
    # --- Analyze and Report Findings ---
    if not search_results.landing_sites:
        print("\n! MISSION FAILURE: No potential landing sites were identified in the operational area.")
        print("Possible reasons:")
        print("  1. No suitable terrain/runways in the search area")
        print("  2. Data source connectivity issues")
        print("  3. Configuration too restrictive (slope, size requirements)")
        return

    print(f"\nSearch complete in {processing_time:.2f} seconds.")
    print(f"Found {len(search_results.landing_sites)} potential landing sites.")
    
    # --- ENHANCED REPORTING ---
    print("\n--- Identified Landing Sites ---")
    print(f"{'#':<3} {'Type':<12} {'Coordinates':<25} {'Orientation':<11} {'Dimensions (m)':<15} {'Surface':<12} {'Score':<6} {'Distance':<8} {'Safety'}")
    print('-'*120)
    
    for rank, site in enumerate(search_results.landing_sites, 1):
        coords_str = f"({site.lat:.4f}, {site.lon:.4f})"
        orientation_str = f"{site.orientation_degrees:.1f}°" if site.orientation_degrees else "N/A"
        dims = f"{site.length_m:.0f}x{site.width_m:.0f}"
        surface = site.surface_type[:11] if site.surface_type else "Unknown"
        score = f"{site.suitability_score}/100"
        distance = f"{site.distance_km:.1f}km"
        safety = "✅" if site.safety_report.is_safe else "❌"
        
        print(f"{rank:<3} {site.site_type:<12} {coords_str:<25} {orientation_str:<11} {dims:<15} {surface:<12} {score:<6} {distance:<8} {safety}")

    # --- Safety Analysis Summary ---
    safe_sites = [s for s in search_results.landing_sites if s.safety_report.is_safe]
    unsafe_sites = [s for s in search_results.landing_sites if not s.safety_report.is_safe]
    
    print(f"\nSafety Analysis:")
    print(f"  Safe sites: {len(safe_sites)}/{len(search_results.landing_sites)}")
    print(f"  Unsafe sites: {len(unsafe_sites)}/{len(search_results.landing_sites)}")
    
    if search_results.landing_sites:
        avg_safety_score = sum(s.safety_report.safety_score for s in search_results.landing_sites) / len(search_results.landing_sites)
        print(f"  Average safety score: {avg_safety_score:.1f}/100")
        
        total_obstacles = sum(s.safety_report.obstacle_count for s in search_results.landing_sites)
        print(f"  Total obstacles detected: {total_obstacles}")

    # --- Generate Interactive Map ---
    print(f"\nGenerating interactive map visualization...")
    visualizer = MapVisualizer()
    
    # Create a mock aircraft state for visualization
    from shallnotcrash.path_planner.data_models import AircraftState
    aircraft_state = AircraftState(
        lat=SEARCH_LAT, 
        lon=SEARCH_LON, 
        alt_ft=5000, 
        heading_deg=0, 
        airspeed_kts=80
    )
    
    # Generate the mission map (without flight paths for now)
    try:
        mission_map = visualizer.create_integrated_mission_map(
            start_state=aircraft_state,
            results=search_results,
            flight_paths={}  # Empty dict since we're not generating paths here
        )
        
        # Save the map
        map_filename = "bikf_landing_sites_map.html"
        visualizer.save_map(mission_map, map_filename)
        print(f"Interactive map saved to '{map_filename}'")
        
    except Exception as e:
        print(f"ERROR during map generation: {e}")
        print("Check if visualization module is properly configured.")

    # --- Save detailed results for later inspection ---
    print(f"\nDetailed site data saved to 'bikf_landing_sites_report.txt'")
    try:
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
            
            f.write("SAFETY SUMMARY:\n")
            f.write(f"  Safe sites: {len(safe_sites)}/{len(search_results.landing_sites)}\n")
            f.write(f"  Average safety score: {avg_safety_score:.1f}/100\n")
            f.write(f"  Total obstacles: {total_obstacles}\n\n")
            
            f.write("DETAILED SITE ANALYSIS:\n")
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
                    for violation in safety.civilian_violations:
                        f.write(f"     - {violation['type']} at {violation['distance_km']:.2f}km\n")
                
                if site.elevation_m is not None:
                    f.write(f"   Elevation: {site.elevation_m}m\n")
                
                # Polygon coordinates info
                if hasattr(site, 'polygon_coords') and site.polygon_coords:
                    f.write(f"   Polygon points: {len(site.polygon_coords)} coordinates\n")
    except Exception as e:
        print(f"ERROR saving report: {e}")

    print("\nDemonstration complete. Use the report file and interactive map for further analysis.")
    print(f"\nNext steps:")
    print(f"  1. Open '{map_filename}' in a web browser to view landing sites")
    print(f"  2. Review 'bikf_landing_sites_report.txt' for detailed analysis")
    print(f"  3. Run path planning to generate optimal routes to selected sites")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_operational_test()
