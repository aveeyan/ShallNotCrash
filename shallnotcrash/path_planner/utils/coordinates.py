# shallnotcrash/path_planner/utils/coordinates.py
"""
Contains coordinate and geodesic calculation utilities.
"""
import math

# Constants
EARTH_RADIUS_NM = 3440.065  # Nautical miles

def haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points
    on the earth (specified in decimal degrees).
    Result is in nautical miles.
    """
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = EARTH_RADIUS_NM * c
    return distance

def destination_point(lat: float, lon: float, bearing_deg: float, distance_nm: float) -> tuple[float, float]:
    """
    Calculates the destination point given a starting point, bearing, and distance.
    """
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)

    angular_distance = distance_nm / EARTH_RADIUS_NM

    lat2_rad = math.asin(math.sin(lat_rad) * math.cos(angular_distance) +
                         math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad))

    lon2_rad = lon_rad + math.atan2(math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
                                    math.cos(angular_distance) - math.sin(lat_rad) * math.sin(lat2_rad))

    return math.degrees(lat2_rad), math.degrees(lon2_rad)