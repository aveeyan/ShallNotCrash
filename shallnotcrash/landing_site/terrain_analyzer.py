# shallnotcrash/landing_site/terrain_analyzer.py
"""
[FULLY OFFLINE - V3]
This version performs all safety and terrain analysis using local data.
Slope calculation now uses local DEM files via Rasterio, removing the final
online bottleneck for maximum performance.
"""
import logging
import math
import os
from typing import List, Dict, Tuple

import numpy as np
import rasterio

from .data_models import SafetyReport

class TerrainAnalyzer:
    """
    Performs fully offline analysis of slope and proximity to obstacles
    using pre-computed spatial indexes and local DEM files.
    """
    def __init__(self, all_nearby_elements: List[Dict], dem_dir_path: str,
                 civilian_exclusion_radius_m: int = 500, max_slope_degrees: float = 2.0):
        
        self.civilian_exclusion_radius_m = civilian_exclusion_radius_m
        self.max_slope_degrees = max_slope_degrees
        
        # --- [OPTIMIZATION 1] Build spatial index for obstacles/civilian areas ---
        self.obstacle_index, self.civilian_index = self._build_spatial_index(all_nearby_elements)
        
        # --- [OPTIMIZATION 2] Open local DEM files for offline slope analysis ---
        self.dem_sources = []
        if os.path.isdir(dem_dir_path):
            self.dem_sources = [rasterio.open(os.path.join(dem_dir_path, f)) 
                                for f in os.listdir(dem_dir_path) if f.endswith('.tif')]
        
        if not self.dem_sources:
            logging.warning(f"No DEM files (.tif) found in {dem_dir_path}. Slope analysis will be skipped.")
        
        logging.info(f"TerrainAnalyzer initialized. Indexed {len(self.obstacle_index)} obstacle cells. Using {len(self.dem_sources)} DEM files.")

    def _get_terrain_slope(self, lat: float, lon: float) -> Tuple[int, float]:
        """[FULLY OFFLINE] Calculates ground slope using local DEM files."""
        if not self.dem_sources:
            return 100, 0.0 # Assume flat if no DEM data is available

        try:
            # Define a 100m sampling box for slope calculation
            offset = 0.00045  # ~50 meters in latitude
            lon_offset = offset / math.cos(math.radians(lat)) # Adjust for longitude
            
            # Rasterio expects (lon, lat) order
            sample_points = [
                (lon, lat), (lon, lat + offset), (lon, lat - offset),
                (lon + lon_offset, lat), (lon - lon_offset, lat)
            ]

            # Extract elevation values from the first DEM source that covers the points
            elevations = []
            for src in self.dem_sources:
                for val in src.sample(sample_points):
                    if val[0] > -1000: # Filter out common no-data values
                        elevations.append(val[0])
                if len(elevations) == 5:
                    break # We have all 5 points from this DEM file
            
            if len(elevations) < 5:
                return 0, 99.0 # Return high slope if data is incomplete

            z_center, z_north, z_south, z_east, z_west = elevations
            
            # Approximate distance in meters between sample points
            dist_meters = 2 * offset * 111111 
            if dist_meters == 0: return 100, 0.0

            slope_rad = np.arctan(np.sqrt(((z_north - z_south) / dist_meters)**2 + ((z_east - z_west) / dist_meters)**2))
            slope_deg = np.degrees(slope_rad)
            
            score = max(0, int(100 - (slope_deg / self.max_slope_degrees) * 100))
            return score, round(slope_deg, 2)
        except Exception:
            return 0, 99.0 # Default to unsafe on error

    def close_dem_sources(self):
        """Closes all open DEM file handles."""
        for src in self.dem_sources:
            src.close()
            
    # --- (The rest of the TerrainAnalyzer class remains the same as the previous fix) ---
    def _build_spatial_index(self, elements: List[Dict]) -> Tuple[Dict, Dict]:
        obstacle_index, civilian_index = {}, {}
        obstacle_tags = {'building', 'tower', 'mast', 'chimney', 'silo', 'water_tower'}
        civilian_tags = {'residential', 'commercial', 'retail', 'industrial', 'school', 'hospital'}
        for element in elements:
            tags, coords = element.get('tags', {}), self._get_coords_from_element(element)
            if not coords: continue
            is_obstacle = any(tag in tags for tag in obstacle_tags)
            is_civilian = any(tag in tags.get('landuse', '') or tag in tags.get('amenity', '') for tag in civilian_tags)
            for lat, lon in coords:
                grid_key = (int(lat * 100), int(lon * 100))
                if is_obstacle:
                    obstacle_index.setdefault(grid_key, []).append((lat, lon))
                if is_civilian:
                    civilian_index.setdefault(grid_key, []).append({'coords': (lat, lon), 'tags': tags})
        return obstacle_index, civilian_index

    def analyze_site(self, lat: float, lon: float, polygon_coords: List[Tuple[float, float]]) -> SafetyReport:
        slope_score, slope_degrees = self._get_terrain_slope(lat, lon)
        obstacle_count = self._count_obstacles_near_site(lat, lon)
        closest_civilian_distance, civilian_violations = self._check_civilian_proximity(lat, lon)
        is_safe = (slope_degrees <= self.max_slope_degrees and closest_civilian_distance >= self.civilian_exclusion_radius_m / 1000 and obstacle_count == 0)
        civilian_score = min(100, int((closest_civilian_distance * 1000 / self.civilian_exclusion_radius_m) * 100))
        obstacle_penalty = min(50, obstacle_count * 25)
        safety_score = max(0, min(slope_score, civilian_score) - obstacle_penalty)
        risk_level = "HIGH"
        if not is_safe:
            if slope_degrees > self.max_slope_degrees: risk_level = f"UNSAFE (Slope > {self.max_slope_degrees}°)"
            elif len(civilian_violations) > 0: risk_level = "UNSAFE (Civilian Area)"
            elif obstacle_count > 0: risk_level = f"UNSAFE ({obstacle_count} Obstacles)"
            else: risk_level = "UNSAFE"
        elif safety_score >= 80: risk_level = "LOW"
        elif safety_score >= 60: risk_level = "MODERATE"
        return SafetyReport(is_safe=is_safe, risk_level=risk_level, safety_score=safety_score, obstacle_count=obstacle_count, closest_civilian_distance_km=closest_civilian_distance, civilian_violations=civilian_violations)

    def _get_relevant_cells(self, lat: float, lon: float) -> List[Tuple[int, int]]:
        cx, cy = int(lat * 100), int(lon * 100)
        return [(cx + dx, cy + dy) for dx in [-1, 0, 1] for dy in [-1, 0, 1]]

    def _count_obstacles_near_site(self, lat: float, lon: float) -> int:
        count = 0
        for cell in self._get_relevant_cells(lat, lon):
            if cell in self.obstacle_index:
                for obs_lat, obs_lon in self.obstacle_index[cell]:
                    if self._distance_meters(lat, lon, obs_lat, obs_lon) < 200:
                        count += 1
        return count

    def _check_civilian_proximity(self, lat: float, lon: float) -> Tuple[float, List[Dict]]:
        closest_dist, violations = float('inf'), []
        for cell in self._get_relevant_cells(lat, lon):
            if cell in self.civilian_index:
                for area in self.civilian_index[cell]:
                    dist_km = self._distance_km(lat, lon, area['coords'][0], area['coords'][1])
                    closest_dist = min(closest_dist, dist_km)
                    if dist_km < self.civilian_exclusion_radius_m / 1000:
                        violations.append({'type': area['tags'].get('landuse', 'unknown'), 'distance_km': dist_km})
        return (closest_dist if closest_dist != float('inf') else 999.0), violations

    def _get_coords_from_element(self, element: Dict) -> List[Tuple[float, float]]:
        geom = element.get('geometry', [])
        if geom: return [(node['lat'], node['lon']) for node in geom if 'lat' in node and 'lon' in node]
        if element.get('type') == 'node': return [(element.get('lat'), element.get('lon'))]
        return []

    def _distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        return self._distance_meters(lat1, lon1, lat2, lon2) / 1000

    def _distance_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        lat1_rad, lat2_rad = math.radians(lat1), math.radians(lat2)
        dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
