# shallnotcrash/landing_site/terrain_analyzer.py
"""
Performs advanced analysis of potential landing sites, integrating both
topographical data (ground slope) and proximity to civilian infrastructure
to generate a comprehensive safety score.
"""
import logging
from typing import List, Dict, Tuple

import numpy as np
import requests
import requests_cache
from retry_requests import retry

from .data_models import SafetyReport
from .utils.coordinates import CoordinateCalculations

class TerrainAndSafetyAnalyzer:
    """
    Analyzes potential landing sites for both terrain flatness (slope) and
    civilian safety (proximity to buildings, schools, etc.).
    """
    CIVILIAN_RISK_TAGS = {
        "building": ["house", "residential", "apartments", "school", "hospital", "church", "retail", "commercial", "industrial"],
        "amenity": ["school", "hospital", "place_of_worship"],
        "landuse": ["residential", "commercial", "industrial"]
    }
    ELEVATION_API_URL = "https://api.open-meteo.com/v1/elevation"

    def __init__(self, exclusion_radius_m: int, max_slope_degrees: float):
        self.exclusion_radius_m = exclusion_radius_m
        self.max_slope_degrees = max_slope_degrees
        cache_session = requests_cache.CachedSession('.cache', expire_after=-1)
        self.session = retry(cache_session, retries=5, backoff_factor=0.2)
        logging.info(f"TerrainAndSafetyAnalyzer initialized. Max Slope: {max_slope_degrees}°, Civilian Exclusion Radius: {exclusion_radius_m}m.")

    def analyze_site(self, site_lat: float, site_lon: float, civilian_risk_elements: List[Dict]) -> SafetyReport:
        """Performs a full safety and terrain analysis on a single site."""
        slope_score, slope_degrees = self._get_slope_score(site_lat, site_lon)
        civilian_score, violations, closest_dist_km = self._get_civilian_risk_score(site_lat, site_lon, civilian_risk_elements)

        final_safety_score = int(slope_score * (civilian_score / 100.0))
        is_safe = final_safety_score >= 70 and slope_degrees <= self.max_slope_degrees

        if slope_degrees > self.max_slope_degrees:
            risk_level = f"UNSAFE (Slope: {slope_degrees:.1f}°)"
        elif final_safety_score < 40:
            risk_level = "HIGH RISK (Civilian)"
        elif final_safety_score < 70:
            risk_level = "CAUTION"
        else:
            risk_level = "SAFE"

        return SafetyReport(
            is_safe=is_safe,
            risk_level=risk_level,
            civilian_violations=violations,
            closest_civilian_distance_km=closest_dist_km,
            obstacle_count=len(violations),
            safety_score=final_safety_score
        )

    def _get_slope_score(self, lat: float, lon: float) -> Tuple[int, float]:
        """Calculates ground slope using a simple, direct JSON API call."""
        try:
            # Define a 5-point grid for gradient calculation
            offset = 0.0009
            lats = [lat, lat + offset, lat - offset, lat, lat]
            lons = [lon, lon, lon, lon + offset, lon - offset]

            # --- CRITICAL PROTOCOL CORRECTION ---
            # The API requires coordinates as a single comma-separated string, not a list.
            # This was the cause of the '400 Bad Request' error.
            params = {
                'latitude': ",".join(map(str, lats)),
                'longitude': ",".join(map(str, lons))
            }

            response = self.session.get(self.ELEVATION_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            elevations = data.get('elevation')

            if not elevations or len(elevations) < 5:
                logging.warning(f"API returned incomplete elevation data for ({lat:.4f}, {lon:.4f}).")
                return 20, 99.0

            z_center, z_north, z_south, z_east, z_west = elevations
            dist_meters = 2 * offset * 111139

            if dist_meters == 0: return 100, 0.0

            dz_ns = z_north - z_south
            dz_ew = z_east - z_west
            
            slope_rad = np.arctan(np.sqrt((dz_ns/dist_meters)**2 + (dz_ew/dist_meters)**2))
            slope_deg = np.degrees(slope_rad)

            score = max(0, 100 - (slope_deg / self.max_slope_degrees) * 100)
            return int(score), round(slope_deg, 2)

        except requests.exceptions.RequestException as e:
            logging.error(f"Network failure during slope calculation for ({lat:.4f}, {lon:.4f}): {e}")
            return 0, 99.0
        except (KeyError, TypeError, ValueError) as e:
            logging.error(f"Data parsing failure during slope calculation for ({lat:.4f}, {lon:.4f}): {e}")
            return 0, 99.0

    def _get_civilian_risk_score(self, site_lat: float, site_lon: float, civilian_risk_elements: List[Dict]) -> Tuple[int, List, float]:
        """Calculates a safety score based on proximity to civilian infrastructure."""
        violations = []
        closest_distance_m = float('inf')

        if not civilian_risk_elements:
            return 100, [], 999.0

        for element in civilian_risk_elements:
            coords = CoordinateCalculations.get_coords_from_element(element)
            if not coords: continue

            center_lat, center_lon = [sum(c) / len(c) for c in zip(*coords)]
            distance_m = CoordinateCalculations.distance_km(site_lat, site_lon, center_lat, center_lon) * 1000

            if distance_m < self.exclusion_radius_m:
                tags = element.get('tags', {})
                risk_type = tags.get('building') or tags.get('amenity') or tags.get('landuse') or "Structure"
                violations.append({"type": risk_type.replace("_", " ").title(), "distance_m": int(distance_m)})

            if distance_m < closest_distance_m:
                closest_distance_m = distance_m

        score = 100
        if closest_distance_m < self.exclusion_radius_m:
            score = int(100 * (closest_distance_m / self.exclusion_radius_m))

        return score, violations, round(closest_distance_m / 1000, 2)