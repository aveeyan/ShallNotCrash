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
from .utils.constants import SiteConstants

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

    def analyze_site(self, site_lat: float, site_lon: float, site_polygon: List[Tuple[float, float]], all_nearby_elements: List[Dict]) -> SafetyReport:
        """Performs a full safety and terrain analysis on a single site."""
        # --- ENHANCEMENT: Perform uncompromising internal obstacle check first ---
        internal_obstacles = self._check_for_internal_obstacles(site_polygon, all_nearby_elements)
        if internal_obstacles:
            logging.warning(f"Site at ({site_lat:.4f}, {site_lon:.4f}) rejected due to {len(internal_obstacles)} internal obstacles.")
            return SafetyReport(
                is_safe=False,
                risk_level="UNSAFE (Internal Obstacles)",
                safety_score=0,
                obstacle_count=len(internal_obstacles),
                closest_civilian_distance_km=0,
                civilian_violations=[{"type": o['type']} for o in internal_obstacles]
            )

        slope_score, slope_degrees = self._get_slope_score(site_lat, site_lon)
        civilian_score, violations, closest_dist_km = self._get_civilian_risk_score(site_lat, site_lon, all_nearby_elements)

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

    def _check_for_internal_obstacles(self, site_polygon: List[Tuple[float, float]], all_elements: List[Dict]) -> List[Dict]:
        """Checks for any defined obstacles physically inside the landing site polygon."""
        internal_obstacles = []
        obstacle_tags = {tag for tags in SiteConstants.OBSTACLES.values() for tag in tags}

        for element in all_elements:
            tags = element.get('tags', {})
            is_obstacle = any(tags.get(key) in values for key, values in SiteConstants.OBSTACLES.items())
            
            if is_obstacle:
                coords = CoordinateCalculations.get_coords_from_element(element)
                if not coords: continue
                
                for lat, lon in coords:
                    if self._is_point_in_polygon(lat, lon, site_polygon):
                        obstacle_type = next((v.replace("_", " ").title() for k, v_list in SiteConstants.OBSTACLES.items() for v in v_list if tags.get(k) == v), "Obstacle")
                        internal_obstacles.append({"type": obstacle_type, "lat": lat, "lon": lon})
                        break
        return internal_obstacles

    def _is_point_in_polygon(self, lat: float, lon: float, polygon: List[Tuple[float, float]]) -> bool:
        """Determines if a point is inside a given polygon using the Ray Casting algorithm."""
        n = len(polygon)
        if n == 0: return False
        inside = False
        p1_lat, p1_lon = polygon[0]
        for i in range(n + 1):
            p2_lat, p2_lon = polygon[i % n]
            if lat > min(p1_lat, p2_lat) and lat <= max(p1_lat, p2_lat) and lon <= max(p1_lon, p2_lon):
                if p1_lat != p2_lat:
                    xinters = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
                    if p1_lon == p2_lon or lon <= xinters:
                        inside = not inside
            p1_lat, p1_lon = p2_lat, p2_lon
        return inside

    def _get_slope_score(self, lat: float, lon: float) -> Tuple[int, float]:
        """Calculates ground slope using a simple, direct JSON API call."""
        try:
            offset = 0.0009
            lats = [lat, lat + offset, lat - offset, lat, lat]
            lons = [lon, lon, lon, lon + offset, lon - offset]
            params = {'latitude': ",".join(map(str, lats)), 'longitude': ",".join(map(str, lons))}
            response = self.session.get(self.ELEVATION_API_URL, params=params)
            response.raise_for_status()
            elevations = response.json().get('elevation')
            if not elevations or len(elevations) < 5: return 20, 99.0
            z_center, z_north, z_south, z_east, z_west = elevations
            dist_meters = 2 * offset * 111139
            if dist_meters == 0: return 100, 0.0
            dz_ns, dz_ew = z_north - z_south, z_east - z_west
            slope_rad = np.arctan(np.sqrt((dz_ns/dist_meters)**2 + (dz_ew/dist_meters)**2))
            slope_deg = np.degrees(slope_rad)
            score = max(0, 100 - (slope_deg / self.max_slope_degrees) * 100)
            return int(score), round(slope_deg, 2)
        except (requests.exceptions.RequestException, KeyError, TypeError, ValueError) as e:
            logging.error(f"Failure during slope calculation for ({lat:.4f}, {lon:.4f}): {e}")
            return 0, 99.0

    def _get_civilian_risk_score(self, site_lat: float, site_lon: float, all_nearby_elements: List[Dict]) -> Tuple[int, List, float]:
        """Calculates a safety score based on proximity to external civilian infrastructure."""
        violations = []
        closest_distance_m = float('inf')
        for element in all_nearby_elements:
            tags = element.get('tags', {})
            is_risk = any(tags.get(key) in values for key, values in self.CIVILIAN_RISK_TAGS.items())
            if is_risk:
                coords = CoordinateCalculations.get_coords_from_element(element)
                if not coords: continue
                center_lat, center_lon = [sum(c) / len(c) for c in zip(*coords)]
                distance_m = CoordinateCalculations.distance_km(site_lat, site_lon, center_lat, center_lon) * 1000
                if distance_m < self.exclusion_radius_m:
                    risk_type = next((v.replace("_", " ").title() for k, v_list in self.CIVILIAN_RISK_TAGS.items() for v in v_list if tags.get(k) == v), "Structure")
                    violations.append({"type": risk_type, "distance_m": int(distance_m)})
                if distance_m < closest_distance_m:
                    closest_distance_m = distance_m
        score = 100
        if closest_distance_m < self.exclusion_radius_m:
            score = int(100 * (closest_distance_m / self.exclusion_radius_m))
        return score, violations, round(closest_distance_m / 1000, 2)