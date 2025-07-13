# shallnotcrash/landing_site/utils/calculations.py
"""
Contains the core logic for evaluating landing sites and constructing
the data acquisition queries sent to the OpenStreetMap Overpass API.

This module is responsible for:
1.  SiteScoring: Translating raw map data into a quantitative suitability score.
2.  OverpassQueryBuilder: Generating efficient, high-success-rate queries to
    acquire the necessary tactical map data, now including unconventional sites.
"""
from typing import Dict, Tuple

class SiteScoring:
    """
    Calculates the suitability of a potential landing site based on its
    physical characteristics, safety, and proximity.
    """
    
    @staticmethod
    def classify_site(tags: Dict) -> Tuple[str, str]:
        """
        Classifies an OSM element into a site type and surface type.
        This has been expanded to recognize more potential landing surfaces.
        
        Args:
            tags: A dictionary of OpenStreetMap tags for an element.
            
        Returns:
            A tuple containing the site_type (e.g., 'runway', 'beach')
            and surface_type (e.g., 'asphalt', 'sand').
        """
        if tags.get('aeroway') in ('runway', 'aerodrome'):
            return 'runway', tags.get('surface', 'asphalt')
        if tags.get('aeroway') == 'taxiway':
            return 'taxiway', tags.get('surface', 'asphalt')
        if tags.get('highway') in ('motorway', 'trunk', 'primary', 'secondary'):
            return 'major_road', tags.get('surface', 'asphalt')
        # --- STRATEGIC ENHANCEMENT ---
        # Identify beaches as potential, last-resort landing sites.
        if tags.get('natural') == 'beach':
            return 'beach', 'sand'
        if tags.get('landuse') in ('farmland', 'meadow', 'grass', 'greenfield'):
            return 'open_field', 'grass'
        if tags.get('leisure') in ('park', 'golf_course', 'pitch'):
            return 'open_field', 'grass'
        
        return 'small_area', 'unknown'

    @staticmethod
    def calculate_suitability(site_type: str, surface: str, length: float, width: float, safety_score: int, distance: float) -> int:
        """
        Calculates a final suitability score from 0 to 100.
        
        The score is a weighted combination of the site's type, surface,
        dimensions, distance, and the comprehensive safety score from the
        TerrainAndSafetyAnalyzer.
        """
        type_scores = {
            'runway': 100,
            'taxiway': 85,
            'major_road': 65, # Increased viability for long, straight roads
            'open_field': 70,
            'beach': 50 # A viable, but not ideal, option
        }
        surface_scores = {
            'asphalt': 10,
            'concrete': 10,
            'grass': 5,
            'gravel': 2,
            'dirt': 1,
            'sand': 3 # Scored appropriately for soft-field landing
        }
        
        base_score = type_scores.get(site_type, 0)
        base_score += surface_scores.get(surface, 0)
        
        length_bonus = min(10, length / 100)
        width_bonus = min(5, width / 10)
        distance_penalty = max(0, distance * 1.5)
        
        # The final score is now critically dependent on the safety analysis.
        # A site with poor safety (low score) will be severely penalized.
        final_score = (base_score + length_bonus + width_bonus - distance_penalty) * (safety_score / 100.0)
        
        return max(0, min(100, int(final_score)))


class OverpassQueryBuilder:
    """
    Constructs optimized, high-precision queries for the Overpass API
    to find all potential landing surfaces.
    """

    @staticmethod
    def build_query(lat: float, lon: float, radius_km: float, timeout_sec: int) -> str:
        """
        Builds a highly efficient Overpass QL query.
        The query now includes tags for beaches to expand the search profile.
        """
        radius_m = radius_km * 1000
        
        target_features = {
            "highway": ["motorway", "trunk", "primary", "secondary"],
            "aeroway": ["runway", "taxiway", "aerodrome"],
            "landuse": ["farmland", "meadow", "grass", "greenfield"],
            "leisure": ["park", "golf_course", "pitch"],
            # --- STRATEGIC ENHANCEMENT ---
            # Add 'natural' tags to the query to find beaches.
            "natural": ["beach"]
        }

        query_parts = []
        for key, values in target_features.items():
            value_regex = "|".join(values)
            query_parts.append(f'way["{key}"~"^{value_regex}$"](around:{radius_m},{lat},{lon});')

        full_query = f"""
        [out:json][timeout:{timeout_sec}];
        (
          {''.join(query_parts)}
        );
        out geom;
        """
        return full_query