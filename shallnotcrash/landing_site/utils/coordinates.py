# shallnotcrash/landing_site/utils/coordinates.py
"""
Provides essential coordinate geometry and calculation utilities.
This module handles distance, dimensions, and polygon manipulation.
"""
import numpy as np
from typing import List, Tuple, Dict

class CoordinateCalculations:
    """A collection of static methods for coordinate-based calculations."""

    @staticmethod
    def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculates the Haversine distance between two points in kilometers."""
        R = 6371
        d_lat = np.radians(lat2 - lat1)
        d_lon = np.radians(lon2 - lon1)
        a = np.sin(d_lat / 2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(d_lon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    @staticmethod
    def get_coords_from_element(element: Dict) -> List[Tuple[float, float]]:
        """Extracts a list of (lat, lon) tuples from an OSM element's geometry."""
        geom = element.get('geometry', [])
        return [(node['lat'], node['lon']) for node in geom if 'lat' in node and 'lon' in node]

    @staticmethod
    def get_dimensions(coords: List[Tuple[float, float]]) -> Tuple[float, float, float]:
        """Calculates the length, width, and orientation of a polygon."""
        if len(coords) < 2: return 0, 0, 0
        
        # This is a rough approximation. For a simple 'way', this is the length.
        # For a closed polygon, this is half the perimeter.
        distances = [CoordinateCalculations.distance_km(coords[i][0], coords[i][1], coords[i+1][0], coords[i+1][1]) * 1000 for i in range(len(coords)-1)]
        length = sum(distances) if len(coords) == 2 else sum(distances) / 2

        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        # A more robust width calculation is needed for complex polygons.
        # This placeholder is a simple bounding box width.
        width_approx_lat = (max(lats) - min(lats)) * 111.32 * 1000
        width_approx_lon = (max(lons) - min(lons)) * 111.32 * np.cos(np.radians(np.mean(lats))) * 1000
        width = min(width_approx_lat, width_approx_lon) if max(width_approx_lat, width_approx_lon) > 0 else 0
        
        dy = coords[1][0] - coords[0][0]
        dx = np.cos(np.radians(coords[0][0])) * (coords[1][1] - coords[0][1])
        orientation = np.degrees(np.arctan2(dy, dx))
        
        return length, max(1, width), (orientation + 360) % 360

    @staticmethod
    def get_point_at_distance_and_bearing(lat: float, lon: float, distance_m: float, bearing_deg: float) -> Tuple[float, float]:
        """Calculates a new coordinate point from a start point, distance, and bearing."""
        R = 6371000  # Earth radius in meters
        lat_rad = np.radians(lat)
        lon_rad = np.radians(lon)
        bearing_rad = np.radians(bearing_deg)
        
        lat2_rad = np.arcsin(np.sin(lat_rad) * np.cos(distance_m / R) +
                             np.cos(lat_rad) * np.sin(distance_m / R) * np.cos(bearing_rad))
        lon2_rad = lon_rad + np.arctan2(np.sin(bearing_rad) * np.sin(distance_m / R) * np.cos(lat_rad),
                                       np.cos(distance_m / R) - np.sin(lat_rad) * np.sin(lat2_rad))
        return np.degrees(lat2_rad), np.degrees(lon2_rad)

    @staticmethod
    def create_polygon_for_runway(lat: float, lon: float, length_m: int, width_m: int, heading: float) -> List[Tuple[float, float]]:
        """Creates an accurate rectangular polygon for a runway."""
        # --- ENHANCEMENT ---
        # Replaced placeholder with accurate trigonometric calculation.
        half_len = length_m / 2
        half_wid = width_m / 2
        
        # Bearings for the 4 corners relative to the runway heading
        h_plus_90 = (heading + 90) % 360
        h_minus_90 = (heading - 90 + 360) % 360

        # Center points of the two ends of the runway
        p1 = CoordinateCalculations.get_point_at_distance_and_bearing(lat, lon, half_len, heading)
        p2 = CoordinateCalculations.get_point_at_distance_and_bearing(lat, lon, half_len, (heading + 180) % 360)

        # Calculate the four corners of the rectangle
        c1 = CoordinateCalculations.get_point_at_distance_and_bearing(p1[0], p1[1], half_wid, h_plus_90)
        c2 = CoordinateCalculations.get_point_at_distance_and_bearing(p1[0], p1[1], half_wid, h_minus_90)
        c3 = CoordinateCalculations.get_point_at_distance_and_bearing(p2[0], p2[1], half_wid, h_minus_90)
        c4 = CoordinateCalculations.get_point_at_distance_and_bearing(p2[0], p2[1], half_wid, h_plus_90)
        
        return [c1, c2, c3, c4]

    @staticmethod
    def simplify_polygon(points: List[Tuple[float, float]], tolerance: float) -> List[Tuple[float, float]]:
        """Simplifies a polygon using the Ramer-Douglas-Peucker algorithm."""
        if not points or len(points) < 3: return points
        
        def get_perp_dist(p, p1, p2):
            x_diff, y_diff = p2[1] - p1[1], p2[0] - p1[0]
            num = abs(y_diff * p[1] - x_diff * p[0] + p2[1] * p1[0] - p2[0] * p1[1])
            den = np.sqrt(y_diff**2 + x_diff**2)
            return 0 if den == 0 else num / den

        max_dist, index = 0, 0
        for i in range(1, len(points) - 1):
            dist = get_perp_dist(points[i], points[0], points[-1])
            if dist > max_dist: max_dist, index = dist, i

        if max_dist > tolerance:
            res1 = CoordinateCalculations.simplify_polygon(points[:index + 1], tolerance)
            res2 = CoordinateCalculations.simplify_polygon(points[index:], tolerance)
            return res1[:-1] + res2
        else:
            return [points[0], points[-1]]