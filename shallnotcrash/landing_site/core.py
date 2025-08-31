# shallnotcrash/landing_site/core.py
"""
[DEFINITIVE CORE - V5.1 - CORRECTED]
This version fixes the NameError by correctly passing the 'analyzer' instance
to all data processing methods.
"""
import logging
from typing import Optional, List, Dict

from .data_models import SearchConfig, LandingSite, SearchResults, Airport
from .apt_dat_loader import AptDatLoader
from .osm_data_handler import OSMDataHandler
from .terrain_analyzer import TerrainAnalyzer
from .utils.calculations import SiteScoring
from .utils.coordinates import CoordinateCalculations

class LandingSiteFinder:
    """Finds landing sites with a clear data priority: Apt.dat > OSM Runways > Other."""
    
    def __init__(self, config: Optional[SearchConfig] = None):
        self.config = config or SearchConfig()
        self.apt_dat_loader = AptDatLoader()
        self.osm_handler = OSMDataHandler(self.config.query_timeout, self.config.cache_enabled)
        logging.info("LandingSiteFinder initialized (Analyzer will be created per-search).")

    def find_sites(self, lat: float, lon: float, dem_dir_path: str) -> SearchResults:
        origin_airport = Airport(lat=lat, lon=lon, name="Search Origin")
        profile = self.config.get_profile_for('cessna_172p')
        
        all_osm_elements = self.osm_handler.fetch_osm_data(lat, lon, self.config.search_radius_km)
        
        # Initialize the analyzer here, so it can build its spatial index once.
        analyzer = TerrainAnalyzer(
            all_nearby_elements=all_osm_elements,
            dem_dir_path=dem_dir_path, # Pass the path here
            civilian_exclusion_radius_m=self.config.civilian_exclusion_radius_m,
            max_slope_degrees=self.config.max_slope_degrees
        )
                
        # Pass this 'analyzer' instance to the processing methods
        apt_runways = self.apt_dat_loader.load_runways_in_radius(lat, lon, self.config.search_radius_km)
        apt_dat_sites = self._process_apt_runways(apt_runways, lat, lon, analyzer, profile)

        osm_runway_elements = [e for e in all_osm_elements if e.get('tags', {}).get('aeroway') == 'runway']
        osm_runway_sites = self._process_osm_runways(osm_runway_elements, lat, lon, analyzer, profile)
        
        other_osm_elements = [e for e in all_osm_elements if e.get('tags', {}).get('aeroway') != 'runway']
        other_osm_sites = self._process_osm_elements(other_osm_elements, lat, lon, analyzer, profile)

        # Combine and deduplicate sites
        combined_runways = self._combine_and_deduplicate(apt_dat_sites, osm_runway_sites)
        all_sites = self._combine_and_deduplicate(combined_runways, other_osm_sites)
        
        filtered_sites = self._filter_taxiways_if_better_options(all_sites)
        
        sorted_sites = sorted(filtered_sites, key=lambda s: s.suitability_score, reverse=True)
        final_sites = sorted_sites[:self.config.max_sites_return]

        analyzer.close_dem_sources()
        
        logging.info(f"Search complete. Found {len(final_sites)} sites. ({len(apt_dat_sites)} from apt.dat)")
        return SearchResults(
            origin_airport=origin_airport,
            landing_sites=final_sites,
            search_parameters=self.config.__dict__
        )

    # --- [FIXED] All processing methods now correctly accept the 'analyzer' parameter ---

    def _process_apt_runways(self, runways: List[Dict], origin_lat: float, origin_lon: float,
                             analyzer: TerrainAnalyzer, profile: Dict) -> List[LandingSite]:
        sites = []
        for runway in runways:
            lat, lon = runway['center_lat'], runway['center_lon']
            length_m, width_m = runway['length_m'], runway['width_m']
            
            if length_m < profile['min_length_m'] or width_m < profile['min_width_m']: continue

            poly_coords = CoordinateCalculations.create_polygon_for_runway(
                lat, lon, int(length_m), int(width_m), runway['orientation_degrees'])
            
            safety_report = analyzer.analyze_site(lat, lon, poly_coords)
            if not safety_report.is_safe: continue

            distance = CoordinateCalculations.distance_km(origin_lat, origin_lon, lat, lon)
            score = SiteScoring.calculate_suitability('runway', runway['surface_type'], length_m, width_m, safety_report.safety_score, distance)

            sites.append(LandingSite(
                lat=lat, lon=lon, length_m=int(length_m), width_m=int(width_m),
                site_type='runway', suitability_score=score, distance_km=round(distance, 2),
                safety_report=safety_report, polygon_coords=poly_coords, surface_type=runway['surface_type'],
                orientation_degrees=runway['orientation_degrees']))
        return sites

    def _process_osm_runways(self, runways: List[Dict], origin_lat: float, origin_lon: float, 
                             analyzer: TerrainAnalyzer, profile: Dict) -> List[LandingSite]:
        sites = []
        for runway_data in runways:
            coords = CoordinateCalculations.get_coords_from_element(runway_data)
            if len(coords) < 2: continue
            
            length_m, width_m, heading = CoordinateCalculations.get_dimensions(coords)
            surface = runway_data.get('tags', {}).get('surface', 'asphalt').lower()

            if length_m < profile['min_length_m']: continue
            if width_m < profile['min_width_m']: width_m = profile['min_width_m'] 

            center_lat, center_lon = [sum(c) / len(c) for c in zip(*coords)]
            poly_coords = CoordinateCalculations.create_polygon_for_runway(
                center_lat, center_lon, int(length_m), int(width_m), heading)
            
            safety_report = analyzer.analyze_site(center_lat, center_lon, poly_coords)
            if not safety_report.is_safe: continue

            distance = CoordinateCalculations.distance_km(origin_lat, origin_lon, center_lat, center_lon)
            score = SiteScoring.calculate_suitability('runway', surface, length_m, width_m, safety_report.safety_score, distance)

            sites.append(LandingSite(
                lat=center_lat, lon=center_lon, length_m=int(length_m), width_m=int(width_m),
                site_type='runway', suitability_score=score, distance_km=round(distance, 2),
                safety_report=safety_report, polygon_coords=poly_coords, surface_type=surface,
                orientation_degrees=heading))
        return sites

    def _process_osm_elements(self, elements: List[Dict], origin_lat: float, origin_lon: float, 
                              analyzer: TerrainAnalyzer, profile: Dict) -> List[LandingSite]:
        sites = []
        processed_ids = set()
        for elem in elements:
            if elem.get('id') in processed_ids: continue
            coords = CoordinateCalculations.get_coords_from_element(elem)
            if len(coords) < 2: continue

            length, width, orientation = CoordinateCalculations.get_dimensions(coords)
            if length < profile['min_length_m'] or width < profile['min_width_m']: continue

            center_lat, center_lon = [sum(c) / len(c) for c in zip(*coords)]
            site_type, surface = SiteScoring.classify_site(elem.get('tags', {}))
            if site_type == 'small_area': continue

            safety_report = analyzer.analyze_site(center_lat, center_lon, coords)
            if not safety_report.is_safe: continue

            distance = CoordinateCalculations.distance_km(origin_lat, origin_lon, center_lat, center_lon)
            score = SiteScoring.calculate_suitability(site_type, surface, length, width, safety_report.safety_score, distance)

            sites.append(LandingSite(
                lat=center_lat, lon=center_lon, length_m=int(length), width_m=int(width),
                site_type=site_type, suitability_score=score, distance_km=round(distance, 2),
                safety_report=safety_report, polygon_coords=coords, surface_type=surface, 
                orientation_degrees=orientation))
            processed_ids.add(elem.get('id'))
        return sites

    def _filter_taxiways_if_better_options(self, sites: List[LandingSite]) -> List[LandingSite]:
        has_runways = any(site.site_type == 'runway' for site in sites)
        if has_runways:
            return [site for site in sites if site.site_type != 'taxiway']
        return sites

    def _combine_and_deduplicate(self, primary: List[LandingSite], secondary: List[LandingSite]) -> List[LandingSite]:
        final_sites = list(primary)
        for sec_site in secondary:
            is_redundant = any(
                CoordinateCalculations.distance_km(sec_site.lat, sec_site.lon, pri_site.lat, pri_site.lon) < 0.5
                for pri_site in primary
            )
            if not is_redundant:
                final_sites.append(sec_site)
        return final_sites
