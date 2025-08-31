# shallnotcrash/landing_site/core.py
"""
The core orchestrator for the landing site detection system. This module
integrates data from various sources, processes it, and provides the final
list of potential landing sites.
"""
import logging
from typing import Optional, List, Dict

from .data_models import SearchConfig, LandingSite, SearchResults, Airport, SafetyReport
from .runway_loader import RunwayLoader
from .osm_data_handler import OSMDataHandler
from .terrain_analyzer import TerrainAnalyzer
from .utils.calculations import SiteScoring
from .utils.coordinates import CoordinateCalculations

class LandingSiteFinder:
    """Main class to find and evaluate emergency landing sites."""
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.runway_loader = RunwayLoader()
        self.osm_handler = OSMDataHandler(self.config.query_timeout, self.config.cache_enabled)
        self.analyzer = TerrainAnalyzer(
            civilian_exclusion_radius_m=self.config.civilian_exclusion_radius_m,
            max_slope_degrees=self.config.max_slope_degrees
        )
        logging.info("LandingSiteFinder initialized and all components linked.")

    def find_sites(self, lat: float, lon: float) -> SearchResults:
        """The main operational method to run a complete search."""
        origin_airport = Airport(lat=lat, lon=lon, name="Search Origin")
        profile = self.config.get_profile_for('cessna_172p')

        fg_runways = self.runway_loader.get_runways(lat, lon, self.config.search_radius_km)
        osm_elements = self.osm_handler.fetch_osm_data(lat, lon, self.config.search_radius_km)

        # --- REFACTOR: All safety analysis is now handled by the analyzer. ---
        # We pass the full list of OSM elements to each processing function.
        primary_sites = self._process_fg_runways(fg_runways, lat, lon, osm_elements, profile)
        secondary_sites = self._process_osm_elements(osm_elements, lat, lon, osm_elements, profile)

        combined_sites = self._combine_and_deduplicate(primary_sites, secondary_sites)
        sorted_sites = sorted(combined_sites, key=lambda s: s.suitability_score, reverse=True)
        final_sites = sorted_sites[:self.config.max_sites_return]

        logging.info(f"Search complete. Found {len(final_sites)} suitable landing sites.")
        return SearchResults(
            origin_airport=origin_airport,
            landing_sites=final_sites,
            search_parameters=self.config.__dict__
        )

    def _process_osm_elements(self, elements: List[Dict], origin_lat: float, origin_lon: float, all_nearby_elements: List[Dict], profile: Dict) -> List[LandingSite]:
        """Processes raw OSM data into a list of LandingSite objects."""
        sites = []
        if not elements: return sites

        for elem in elements:
            coords = CoordinateCalculations.get_coords_from_element(elem)
            if len(coords) < 2: continue

            simplified_coords = CoordinateCalculations.simplify_polygon(coords, tolerance=0.0001)
            if len(simplified_coords) < 2: continue

            length, width, orientation = CoordinateCalculations.get_dimensions(simplified_coords)
            if length < profile['min_length_m'] or width < profile['min_width_m']: continue

            center_lat, center_lon = [sum(c) / len(c) for c in zip(*simplified_coords)]
            site_type, surface = SiteScoring.classify_site(elem.get('tags', {}))
            if site_type == 'small_area': continue

            # --- ENHANCEMENT: Pass the site polygon for internal obstacle checks ---
            safety_report = self.analyzer.analyze_site(
                lat=center_lat, 
                lon=center_lon, 
                polygon_coords=simplified_coords, 
                all_nearby_elements=all_nearby_elements
            )
            if not safety_report.is_safe:
                continue

            distance = CoordinateCalculations.distance_km(origin_lat, origin_lon, center_lat, center_lon)
            score = SiteScoring.calculate_suitability(site_type, surface, length, width, safety_report.safety_score, distance)

            sites.append(LandingSite(
                lat=center_lat, 
                lon=center_lon, 
                length_m=int(length), 
                width_m=int(width),
                site_type=site_type, 
                suitability_score=score, 
                distance_km=round(distance, 2),
                safety_report=safety_report, 
                polygon_coords=simplified_coords,
                surface_type=surface, 
                orientation_degrees=orientation
            ))
        return sites

    def _process_fg_runways(self, runways: List[Dict], origin_lat: float, origin_lon: float, all_nearby_elements: List[Dict], profile: Dict) -> List[LandingSite]:
        """Processes FlightGear runway data (as dictionaries) into LandingSite objects."""
        sites = []
        for runway_data in runways:
            # Handle runway data as dictionary
            length_ft = runway_data.get('length_ft', 0)
            width_ft = runway_data.get('width_ft', 0)
            runway_lat = runway_data.get('lat', 0)
            runway_lon = runway_data.get('lon', 0)
            heading = runway_data.get('heading', 0)
            surface = runway_data.get('surface', 'unknown')
            elevation_ft = runway_data.get('elevation_ft', 0)
            
            length_m = int(length_ft * 0.3048)
            width_m = int(width_ft * 0.3048)
            if length_m < profile['min_length_m'] or width_m < profile['min_width_m']: 
                continue

            poly_coords = CoordinateCalculations.create_polygon_for_runway(
                runway_lat, runway_lon, length_m, width_m, heading
            )
            
            # --- ENHANCEMENT: Pass the runway polygon for internal obstacle checks ---
            safety_report = self.analyzer.analyze_site(
                lat=runway_lat, 
                lon=runway_lon, 
                polygon_coords=poly_coords, 
                all_nearby_elements=all_nearby_elements
            )
            if not safety_report.is_safe:
                continue

            distance = CoordinateCalculations.distance_km(origin_lat, origin_lon, runway_lat, runway_lon)
            score = SiteScoring.calculate_suitability('runway', surface.lower(), length_m, width_m, safety_report.safety_score, distance)

            sites.append(LandingSite(
                lat=runway_lat, 
                lon=runway_lon, 
                length_m=length_m, 
                width_m=width_m,
                site_type='runway', 
                suitability_score=score, 
                distance_km=round(distance, 2),
                safety_report=safety_report, 
                polygon_coords=poly_coords, 
                surface_type=surface,
                orientation_degrees=heading, 
                elevation_m=int(elevation_ft * 0.3048)
            ))
        return sites

    def _combine_and_deduplicate(self, primary_sites: List[LandingSite], secondary_sites: List[LandingSite]) -> List[LandingSite]:
        """Combines and de-duplicates sites, prioritizing primary runways."""
        final_sites = list(primary_sites)
        for osm_site in secondary_sites:
            is_redundant = any(
                CoordinateCalculations.distance_km(osm_site.lat, osm_site.lon, runway.lat, runway.lon) < 0.5
                for runway in primary_sites
            )
            if not is_redundant:
                final_sites.append(osm_site)
        return final_sites
