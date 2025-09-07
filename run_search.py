# ~/Documents/shallnotcrash/run_search.py
import os
import sys

# Add the project root to the Python path to ensure imports work correctly
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.non_runway_finder import OfflineSiteFinder, CESSNA_172P_PROFILE

def main():
    """
    Main execution script to find all types of potential landing sites
    for a specified location.
    """
    # --- Configuration ---
    # BIKF Keflavik Airport Coordinates
    SEARCH_LAT, SEARCH_LON = 63.9850, -22.6056
    SEARCH_RADIUS_KM = 50

    # --- Set up paths to your offline data ---
    osm_pbf_path = os.path.join(project_root, "shallnotcrash", "landing_site", "osm", "iceland-latest.osm.pbf")
    dem_dir_path = os.path.join(project_root, "shallnotcrash", "landing_site", "osm", "rasters")

    print("--- Starting Landing Site Search ---")
    print(f"Center: BIKF ({SEARCH_LAT}, {SEARCH_LON}), Radius: {SEARCH_RADIUS_KM}km")
    print("-" * 40)

    # --- Step 1: Find Official Runways ---
    print("\n[1] Searching for official runways (Apt.dat + OSM)...")
    runway_finder = LandingSiteFinder()
    
    # [FIX] Pass the 'dem_dir_path' to the find_sites method
    runway_results = runway_finder.find_sites(SEARCH_LAT, SEARCH_LON, dem_dir_path)

    print(f"\nFound {len(runway_results.landing_sites)} suitable sites (Top {len(runway_results.landing_sites)}):")
    for i, site in enumerate(runway_results.landing_sites):
        print(f"  > Runway #{i+1}: Score {site.suitability_score}, Length {site.length_m:.0f}m, Surface: {site.surface_type.title()}")

    print("-" * 40)

    # --- Step 2: Find Offline Non-Runway Sites ---
    print("\n[2] Searching for non-runway sites using offline data...")
    try:
        offline_finder = OfflineSiteFinder(osm_pbf_path, dem_dir_path)
        non_runway_sites = offline_finder.find_sites(
            SEARCH_LAT, SEARCH_LON, SEARCH_RADIUS_KM, CESSNA_172P_PROFILE
        )

        print(f"\nFound {len(non_runway_sites)} potential non-runway sites (fields, roads, etc.):")
        for i, site in enumerate(non_runway_sites[:10]):
            tags = site['tags']
            site_type = tags.get('landuse', tags.get('highway', 'Unknown')).replace('_', ' ').title()
            print(
                f"  > Site #{i+1}: Type: {site_type:<15} | "
                f"Length: {site['length_m']:.0f}m | "
                f"Slope: {site['slope_deg']:.2f}°"
            )
        
        offline_finder.close()
    except (FileNotFoundError, NotADirectoryError, NameError, ImportError) as e:
        print(f"\n[!] Could not run offline search. Error: {e}")
        print("    Please ensure 'osmium', 'rasterio', etc. are installed and paths are correct.")

    print("\n--- Search Complete ---")

if __name__ == "__main__":
    main()