# shallnotcrash/landing_site/utils/calculations.py
"""
[ENHANCED SITE SCORING - V2]
Improved scoring to prioritize runways over other options.
"""
from typing import Dict, Tuple

class SiteScoring:
    """
    Calculates the suitability of potential landing sites with runway priority.
    """
    
    @staticmethod
    def classify_site(tags: Dict) -> Tuple[str, str]:
        """
        Classifies OSM elements with runway priority.
        """
        aeroway = tags.get('aeroway', '')
        
        # Runways get highest priority
        if aeroway == 'runway':
            return 'runway', tags.get('surface', 'asphalt')
        
        # Other aviation infrastructure
        if aeroway in ('aerodrome', 'airfield'):
            return 'airfield', tags.get('surface', 'asphalt')
            
        # Taxiways are lower priority
        if aeroway == 'taxiway':
            return 'taxiway', tags.get('surface', 'asphalt')
            
        # Road and field options
        if tags.get('highway') in ('motorway', 'trunk', 'primary', 'secondary'):
            return 'major_road', tags.get('surface', 'asphalt')
            
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
        Enhanced scoring with strong runway preference.
        """
        # Runways get massive bonus
        type_scores = {
            'runway': 200,  # Double score for runways
            'airfield': 150,
            'taxiway': 60,  # Reduced score for taxiways
            'major_road': 65,
            'open_field': 70,
            'beach': 50
        }
        
        surface_scores = {
            'asphalt': 20, 'concrete': 25, 'grass': 10,
            'gravel': 5, 'dirt': 1, 'sand': 3
        }
        
        base_score = type_scores.get(site_type, 0)
        base_score += surface_scores.get(surface, 0)
        
        # Size bonuses
        length_bonus = min(20, length / 50)  # More generous for larger sites
        width_bonus = min(10, width / 5)
        
        # Distance penalty (less severe for excellent sites)
        distance_penalty = max(0, distance * (2 if site_type == 'runway' else 1.5))
        
        # Safety is critical
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
        The query is now enhanced to include smaller airstrips and potential obstacles.
        """
        radius_m = radius_km * 1000
        
        target_features = {
            # --- ENHANCEMENT: Added 'landing_strip' and other variations ---
            "aeroway": ["runway", "taxiway", "aerodrome", "airstrip", "landing_strip"],
            "highway": ["motorway", "trunk", "primary", "secondary"],
            "landuse": ["farmland", "meadow", "grass", "greenfield", "recreation_ground", "residential", "commercial", "industrial"],
            "leisure": ["park", "golf_course", "pitch", "track", "stadium"],
            "natural": ["beach", "grassland"],
            "building": ["yes", "house", "apartments", "industrial", "school", "hospital"],
            "power": ["line", "tower"],
            "natural": ["tree", "scrub", "wood"]
        }

        query_parts = []
        for key, values in target_features.items():
            value_regex = "|".join(values)
            query_parts.append(f'way["{key}"~"^{value_regex}$"](around:{radius_m},{lat},{lon});')
            query_parts.append(f'relation["{key}"~"^{value_regex}$"](around:{radius_m},{lat},{lon});')

        full_query = f"""
        [out:json][timeout:{timeout_sec}];
        (
          {''.join(query_parts)}
        );
        out geom;
        """
        return full_query