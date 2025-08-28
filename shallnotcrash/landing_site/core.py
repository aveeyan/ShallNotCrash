# shallnotcrash/landing_site/core.py
"""
[RE-ARCHITECTED - V2]
This module contains the core logic for finding and evaluating potential
landing sites. It acts as the primary orchestrator for the landing_site package.

This version corrects a critical ImportError by removing invalid dependencies
and using the canonical data models and loaders from the established public APIs.
"""
import logging
from typing import List

# --- [FIX] Import the canonical Runway object from the central data_models ---
from ..path_planner.data_models import Runway

# --- [FIX] Import this package's output data model ---
from .data_models import LandingSite

# --- [FIX] Import the correct network loader from this package ---
from .runway_loader import RunwayLoader

# --- [FIX] Import utility functions from the path_planner's public API ---
class LandingSiteFinder:
    
    """
    Orchestrates the process of finding landing sites by using loaders
    to gather data and then processing that data into a list of
    structured LandingSite objects.
    """
    def __init__(self):
        self.osm_loader = RunwayLoader()
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("LandingSiteFinder initialized with network (OSM) loader.")

    def find_sites(self, lat: float, lon: float, radius_km: int) -> List[LandingSite]:
        """
        Finds and processes landing sites within a given radius.

        1. Fetches raw runway data using the network loader.
        2. Parses the raw data into canonical Runway objects.
        3. Groups runways into LandingSite objects.
        """
        logging.info(f"Finding landing sites near ({lat}, {lon}) with radius {radius_km}km.")
        raw_osm_data = self.osm_loader.get_runways(lat, lon, radius_km)
        
        if not raw_osm_data:
            logging.warning("The network loader returned no data. No landing sites found.")
            return []
        
        # The parsing logic, once part of the test script, is now correctly
        # centralized here as part of the site-finding process.
        osm_runways = self._parse_osm_data_to_runways(raw_osm_data)
        
        # For simplicity, we will treat each runway as part of its own landing site.
        # A more complex implementation could group runways by airport.
        landing_sites = []
        for runway in osm_runways:
            site = LandingSite(
                name=f"Site for {runway.name}",
                center_lat=runway.center_lat,
                center_lon=runway.center_lon,
                runways=[runway]
            )
            landing_sites.append(site)
            
        logging.info(f"Found and processed {len(landing_sites)} potential landing sites.")
        return landing_sites

    def _parse_osm_data_to_runways(self, osm_data: list) -> List[Runway]:
        """
        Parses the raw JSON from the Overpass API into a list of canonical Runway objects.
        """
        from ..path_planner import get_midpoint, get_bearing
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
                
                # OSM data for length/width can be missing, default to 0.
                try:
                    length = float(tags.get('length', 0))
                except (ValueError, TypeError):
                    length = 0.0 # Handle cases where length is not a valid number
                
                try:
                    width = float(tags.get('width', 0))
                except (ValueError, TypeError):
                    width = 0.0 # Handle cases where width is not a valid number

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
        return runways
        