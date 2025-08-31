# shallnotcrash/landing_site/terrain_analyzer.py
"""
Performs terrain and safety analysis for landing site validation.

This module analyzes terrain conditions, obstacle presence, and civilian area
proximity to determine the safety and suitability of potential landing sites.
"""
import logging
from typing import List, Dict, Tuple, Optional

import numpy as np
import requests
import requests_cache
from retry_requests import retry

from .data_models import SafetyReport

class TerrainAnalyzer:
    """
    Analyzes terrain for slope and proximity to obstacles and civilian areas.
    """
    def __init__(self, civilian_exclusion_radius_m: int = 500, max_slope_degrees: float = 2.0):
        self.civilian_exclusion_radius_m = civilian_exclusion_radius_m
        self.max_slope_degrees = max_slope_degrees
        
        # Setup cached session for API requests
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600 * 24 * 7)  # Cache for 1 week
        self.session = retry(cache_session, retries=5, backoff_factor=0.2)
        
        logging.info(f"TerrainAnalyzer initialized. Max Slope: {self.max_slope_degrees}°, Civilian Exclusion: {self.civilian_exclusion_radius_m}m")

    def analyze_site(self, lat: float, lon: float, polygon_coords: List[Tuple[float, float]], all_nearby_elements: List[Dict]) -> SafetyReport:
        """
        Performs comprehensive safety analysis for a landing site.
        
        Args:
            lat: Center latitude of the site
            lon: Center longitude of the site  
            polygon_coords: Polygon coordinates defining the site boundaries
            all_nearby_elements: All OSM elements in the search area for obstacle detection
            
        Returns:
            SafetyReport with safety assessment details
        """
        # Analyze terrain slope
        slope_score, slope_degrees = self._get_terrain_slope(lat, lon)
        
        # Check for obstacles within and around the site
        obstacle_count = self._count_obstacles_near_site(lat, lon, polygon_coords, all_nearby_elements)
        
        # Check proximity to civilian areas
        closest_civilian_distance, civilian_violations = self._check_civilian_proximity(lat, lon, all_nearby_elements)
        
        # Determine overall safety
        is_safe = (
            slope_degrees <= self.max_slope_degrees and
            closest_civilian_distance >= self.civilian_exclusion_radius_m / 1000 and  # Convert to km
            len(civilian_violations) == 0
        )
        
        # Calculate composite safety score
        civilian_score = min(100, int((closest_civilian_distance * 1000 / self.civilian_exclusion_radius_m) * 100))
        obstacle_penalty = min(50, obstacle_count * 10)  # Each obstacle reduces score by 10, max penalty 50
        safety_score = max(0, min(slope_score, civilian_score) - obstacle_penalty)
        
        # Determine risk level
        if not is_safe:
            if slope_degrees > self.max_slope_degrees:
                risk_level = f"UNSAFE (Slope: {slope_degrees:.1f}° > {self.max_slope_degrees}°)"
            elif len(civilian_violations) > 0:
                risk_level = f"UNSAFE (Too close to civilian areas)"
            else:
                risk_level = "UNSAFE (Multiple factors)"
        else:
            if safety_score >= 80:
                risk_level = "LOW"
            elif safety_score >= 60:
                risk_level = "MODERATE"
            else:
                risk_level = "HIGH"

        return SafetyReport(
            is_safe=is_safe,
            risk_level=risk_level,
            safety_score=safety_score,
            obstacle_count=obstacle_count,
            closest_civilian_distance_km=closest_civilian_distance,
            civilian_violations=civilian_violations
        )

    def _get_terrain_slope(self, lat: float, lon: float) -> Tuple[int, float]:
        """
        Calculates ground slope using the Open-Meteo elevation API.
        Returns (score, slope_in_degrees)
        """
        try:
            # Define a 100m sampling box around the center point for slope calculation
            # 1 degree of latitude is ~111.1 km. 0.00045 degrees is ~50 meters.
            offset = 0.00045 
            lats = [lat, lat + offset, lat - offset, lat, lat]
            lons = [lon, lon, lon, lon + offset, lon - offset]
            
            params = {
                'latitude': ",".join(map(str, lats)), 
                'longitude': ",".join(map(str, lons))
            }
            
            response = self.session.get('https://api.open-meteo.com/v1/elevation', params=params)
            response.raise_for_status()
            
            elevations = response.json().get('elevation')
            if not elevations or len(elevations) < 5:
                logging.warning(f"Incomplete elevation data for ({lat:.4f}, {lon:.4f})")
                return 0, 99.0  # Return minimum score and a high slope value

            z_center, z_north, z_south, z_east, z_west = elevations
            
            # Distance between North-South and East-West sample points in meters
            # Approximate: 1 degree latitude = 111,111 meters
            dist_meters = 2 * offset * 111111
            if dist_meters == 0: 
                return 100, 0.0  # No distance means flat

            dz_ns = z_north - z_south
            dz_ew = z_east - z_west
            
            slope_rad = np.arctan(np.sqrt((dz_ns / dist_meters)**2 + (dz_ew / dist_meters)**2))
            slope_deg = np.degrees(slope_rad)
            
            score = max(0, int(100 - (slope_deg / self.max_slope_degrees) * 100))
            
            return score, round(slope_deg, 2)
            
        except (requests.exceptions.RequestException, KeyError, TypeError, ValueError) as e:
            logging.error(f"Failure during slope calculation for ({lat:.4f}, {lon:.4f}): {e}")
            return 0, 99.0  # Return minimum score and a high slope value

    def _count_obstacles_near_site(self, lat: float, lon: float, polygon_coords: List[Tuple[float, float]], all_nearby_elements: List[Dict]) -> int:
        """
        Counts obstacles (buildings, towers, etc.) near or within the landing site.
        """
        obstacle_count = 0
        obstacle_tags = ['building', 'tower', 'mast', 'chimney', 'silo', 'water_tower']
        
        for element in all_nearby_elements:
            tags = element.get('tags', {})
            
            # Check if element is an obstacle
            is_obstacle = any(tag in tags for tag in obstacle_tags)
            if not is_obstacle:
                continue
                
            # Get element coordinates
            element_coords = self._get_coords_from_element(element)
            if not element_coords:
                continue
                
            # Check if obstacle is within or very close to the site
            for coord_lat, coord_lon in element_coords:
                distance_m = self._distance_meters(lat, lon, coord_lat, coord_lon)
                if distance_m < 200:  # Within 200m of site center
                    obstacle_count += 1
                    break  # Count each element only once
                    
        return obstacle_count

    def _check_civilian_proximity(self, lat: float, lon: float, all_nearby_elements: List[Dict]) -> Tuple[float, List[Dict]]:
        """
        Checks proximity to civilian areas (residential, commercial, schools, hospitals).
        Returns (closest_distance_km, list_of_violations)
        """
        civilian_tags = [
            'residential', 'commercial', 'retail', 'industrial', 'school', 
            'hospital', 'clinic', 'university', 'college', 'kindergarten'
        ]
        
        closest_distance = float('inf')
        violations = []
        
        for element in all_nearby_elements:
            tags = element.get('tags', {})
            
            # Check if element is a civilian area
            is_civilian = any(tag in tags.get('landuse', '') or tag in tags.get('amenity', '') or tag in tags.get('building', '') for tag in civilian_tags)
            if not is_civilian:
                continue
                
            # Get element coordinates
            element_coords = self._get_coords_from_element(element)
            if not element_coords:
                continue
                
            # Find closest point of civilian area to landing site
            for coord_lat, coord_lon in element_coords:
                distance_km = self._distance_km(lat, lon, coord_lat, coord_lon)
                closest_distance = min(closest_distance, distance_km)
                
                # Check for violations
                if distance_km < self.civilian_exclusion_radius_m / 1000:
                    violations.append({
                        'type': tags.get('landuse') or tags.get('amenity') or tags.get('building', 'unknown'),
                        'distance_km': distance_km,
                        'coordinates': (coord_lat, coord_lon)
                    })
        
        return closest_distance if closest_distance != float('inf') else 10.0, violations

    def _get_coords_from_element(self, element: Dict) -> List[Tuple[float, float]]:
        """Extract coordinates from an OSM element."""
        if element.get('type') == 'node':
            lat = element.get('lat')
            lon = element.get('lon')
            if lat is not None and lon is not None:
                return [(lat, lon)]
        elif element.get('type') == 'way':
            # For ways, we need to look up the actual node coordinates
            # Since we don't have the node lookup here, we'll use the geometry if available
            geometry = element.get('geometry', [])
            if geometry:
                coords = []
                for point in geometry:
                    lat = point.get('lat')
                    lon = point.get('lon')
                    if lat is not None and lon is not None:
                        coords.append((lat, lon))
                return coords
        elif element.get('type') == 'relation':
            # For relations, try to get center coordinates if available
            center = element.get('center')
            if center:
                lat = center.get('lat')
                lon = center.get('lon')
                if lat is not None and lon is not None:
                    return [(lat, lon)]
        return []

    def _distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers."""
        return self._distance_meters(lat1, lon1, lat2, lon2) / 1000

    def _distance_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in meters using Haversine formula."""
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = np.radians(lat1)
        lat2_rad = np.radians(lat2)
        delta_lat = np.radians(lat2 - lat1)
        delta_lon = np.radians(lon2 - lon1)
        
        a = (np.sin(delta_lat / 2) * np.sin(delta_lat / 2) + 
             np.cos(lat1_rad) * np.cos(lat2_rad) * 
             np.sin(delta_lon / 2) * np.sin(delta_lon / 2))
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        
        return R * c
