#!/usr/bin/env python3
"""
Debug version to check visualization issues
"""
import sys
import logging
from pathlib import Path
import time

sys.path.append(str(Path(__file__).resolve().parent.parent))

from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.landing_site.data_models import SearchConfig
from shallnotcrash.landing_site.visualization import MapVisualizer

# Parameters
SCENARIO_NAME = "Debug - Keflavík Visualization"
SEARCH_LAT = 63.9850
SEARCH_LON = -22.6056
SEARCH_RADIUS_KM = 5  # Smaller radius for debugging

def debug_visualization():
    print("=== DEBUGGING VISUALIZATION ===")
    
    config = SearchConfig(
        search_radius_km=SEARCH_RADIUS_KM,
        max_sites_return=5
    )
    finder = LandingSiteFinder(config)
    
    search_results = finder.find_sites(lat=SEARCH_LAT, lon=SEARCH_LON)
    
    print(f"Found {len(search_results.landing_sites)} sites")
    
    # Debug each site's polygon data
    for i, site in enumerate(search_results.landing_sites, 1):
        print(f"\nSite {i}: {site.site_type}")
        print(f"  Coords: ({site.lat:.6f}, {site.lon:.6f})")
        print(f"  Has polygon_coords: {hasattr(site, 'polygon_coords')}")
        if hasattr(site, 'polygon_coords'):
            print(f"  Polygon points: {len(site.polygon_coords) if site.polygon_coords else 0}")
            if site.polygon_coords:
                print(f"  First point: {site.polygon_coords[0]}")
    
    # Test basic map creation
    visualizer = MapVisualizer()
    
    # Create a simple map with just the center point
    from folium import Map
    simple_map = Map(location=[SEARCH_LAT, SEARCH_LON], zoom_start=12)
    
    # Try adding sites manually
    for site in search_results.landing_sites:
        if hasattr(site, 'polygon_coords') and site.polygon_coords:
            from folium import Polygon
            Polygon(
                locations=site.polygon_coords,
                color='green',
                fill=True,
                fill_color='green',
                fill_opacity=0.4,
                popup=f"{site.site_type}: {site.length_m}x{site.width_m}m"
            ).add_to(simple_map)
        else:
            # Fallback: just add a marker
            from folium import Marker
            Marker(
                location=[site.lat, site.lon],
                popup=f"{site.site_type}: No polygon data"
            ).add_to(simple_map)
    
    simple_map.save("debug_map.html")
    print("Debug map saved to 'debug_map.html'")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Enable debug logging
    debug_visualization()
