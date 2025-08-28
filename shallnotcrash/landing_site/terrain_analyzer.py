# shallnotcrash/path_planner/terrain_analyzer.py
"""
[NEW MODULE - ARCHITECTURALLY ALIGNED]
Performs terrain and safety analysis for flight path validation.

This module is the designated home for all terrain-related logic, now
correctly integrated into the 'path_planner' package. It depends on the
unified data models and utilities of this package, not on deprecated,
isolated code from the old 'landing_site' structure.
"""
import logging
from typing import List, Dict, Tuple

import numpy as np
import requests
import requests_cache
from retry_requests import retry

# --- [FIX] Correctly import from the unified path_planner module structure ---
from .data_models import SafetyReport
from ..path_planner.utils.calculations import is_point_in_polygon
from ..path_planner.utils.coordinates import haversine_distance_nm
from ..path_planner.constants import PlannerConstants, SiteAnalysis

class TerrainAnalyzer:
    """
    Analyzes terrain for slope and proximity to obstacles and civilian areas.
    The name is simplified to reflect its core purpose within the new architecture.
    """
    def __init__(self, max_slope_degrees: float = SiteAnalysis.MAX_SLOPE_DEGREES):
        self.max_slope_degrees = max_slope_degrees
        
        # The session setup is robust and will be retained.
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600 * 24 * 7) # Cache for 1 week
        self.session = retry(cache_session, retries=5, backoff_factor=0.2)
        
        logging.info(f"TerrainAnalyzer initialized. Max Slope: {self.max_slope_degrees}°")

    def analyze_path_corridor(self, waypoints: List[Tuple[float, float]]) -> SafetyReport:
        """
        Performs a full safety and terrain analysis on a corridor defined by waypoints.
        This is a placeholder for a more advanced corridor analysis. For now, it
        analyzes the midpoint of the path.
        """
        # This is a simplified analysis. A true implementation would check the entire corridor.
        if len(waypoints) < 2:
            return SafetyReport(is_safe=False, risk_level="UNSAFE (Path Too Short)", safety_score=0)

        # Analyze the terrain at the midpoint of the path as a representative sample.
        mid_lat = (waypoints[0][0] + waypoints[-1][0]) / 2
        mid_lon = (waypoints[0][1] + waypoints[-1][1]) / 2

        slope_score, slope_degrees = self._get_terrain_slope(mid_lat, mid_lon)

        # For now, we only check slope. Obstacle checks would be added here.
        is_safe = slope_degrees <= self.max_slope_degrees
        
        if not is_safe:
            risk_level = f"UNSAFE (Slope: {slope_degrees:.1f}° > {self.max_slope_degrees}°)"
            safety_score = 0
        else:
            risk_level = "SAFE"
            # Score is inversely proportional to slope
            safety_score = int(max(0, 100 - (slope_degrees / self.max_slope_degrees) * 100))

        return SafetyReport(
            is_safe=is_safe,
            risk_level=risk_level,
            safety_score=safety_score,
            # The following are placeholders for a full obstacle analysis
            obstacle_count=0,
            closest_civilian_distance_km=float('inf'),
            civilian_violations=[]
        )

    def _get_terrain_slope(self, lat: float, lon: float) -> Tuple[int, float]:
        """
        Calculates ground slope using the Open-Meteo elevation API.
        The core logic is sound, but it now uses centralized constants.
        """
        try:
            # Define a 100m sampling box around the center point for slope calculation
            # 1 degree of latitude is ~111.1 km. 0.00045 degrees is ~50 meters.
            offset = 0.00045 
            lats = [lat, lat + offset, lat - offset, lat, lat]
            lons = [lon, lon, lon, lon + offset, lon - offset]
            
            params = {'latitude': ",".join(map(str, lats)), 'longitude': ",".join(map(str, lons))}
            
            response = self.session.get(SiteAnalysis.ELEVATION_API_URL, params=params)
            response.raise_for_status()
            
            elevations = response.json().get('elevation')
            if not elevations or len(elevations) < 5:
                logging.warning(f"Incomplete elevation data for ({lat:.4f}, {lon:.4f})")
                return 0, 99.0 # Return minimum score and a high slope value

            z_center, z_north, z_south, z_east, z_west = elevations
            
            # Distance between North-South and East-West sample points in meters
            dist_meters = haversine_distance_nm(lat + offset, lon, lat - offset, lon) * PlannerConstants.METERS_PER_NAUTICAL_MILE
            if dist_meters == 0: return 100, 0.0 # No distance means flat

            dz_ns = z_north - z_south
            dz_ew = z_east - z_west
            
            slope_rad = np.arctan(np.sqrt((dz_ns / dist_meters)**2 + (dz_ew / dist_meters)**2))
            slope_deg = np.degrees(slope_rad)
            
            score = max(0, 100 - (slope_deg / self.max_slope_degrees) * 100)
            
            return int(score), round(slope_deg, 2)
            
        except (requests.exceptions.RequestException, KeyError, TypeError, ValueError) as e:
            logging.error(f"Failure during slope calculation for ({lat:.4f}, {lon:.4f}): {e}")
            return 0, 99.0 # Return minimum score and a high slope value
        