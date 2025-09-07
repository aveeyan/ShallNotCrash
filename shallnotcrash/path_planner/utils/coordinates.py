# shallnotcrash/path_planner/utils/coordinates.py
"""
[REWORKED - V9 - DIAGNOSTIC]
Core coordinate geometry. Logging is omitted here as these are high-frequency,
low-level functions and are unlikely to be the source of logical error.
"""
import math
from ..constants import PlannerConstants

def haversine_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlon = lon2_rad - lon1_rad; dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return PlannerConstants.EARTH_RADIUS_NM * c

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    initial_bearing = math.atan2(y, x)
    return (math.degrees(initial_bearing) + 360) % 360

def destination_point(lat: float, lon: float, bearing_deg: float, distance_nm: float) -> tuple[float, float]:
    lat_rad = math.radians(lat); lon_rad = math.radians(lon); bearing_rad = math.radians(bearing_deg)
    angular_distance = distance_nm / PlannerConstants.EARTH_RADIUS_NM
    dest_lat_rad = math.asin(math.sin(lat_rad) * math.cos(angular_distance) +
                             math.cos(lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad))
    dest_lon_rad = lon_rad + math.atan2(math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(lat_rad),
                                        math.cos(angular_distance) - math.sin(lat_rad) * math.sin(dest_lat_rad))
    return math.degrees(dest_lat_rad), math.degrees(dest_lon_rad)

# --- Compatibility Layer for E073 and other scripts ---

def get_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """[COMPATIBILITY] Alias for calculate_bearing."""
    return calculate_bearing(lat1, lon1, lat2, lon2)

def get_midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """[ADDED] Calculates the midpoint between two coordinates."""
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    Bx = math.cos(lat2_rad) * math.cos(dlon)
    By = math.cos(lat2_rad) * math.sin(dlon)

    lat_mid_rad = math.atan2(
        math.sin(lat1_rad) + math.sin(lat2_rad),
        math.sqrt((math.cos(lat1_rad) + Bx)**2 + By**2)
    )
    lon_mid_rad = lon1_rad + math.atan2(By, math.cos(lat1_rad) + Bx)

    return math.degrees(lat_mid_rad), math.degrees(lon_mid_rad)

def get_destination_point(lat: float, lon: float, bearing_deg: float, distance_nm: float) -> tuple[float, float]:
    """[COMPATIBILITY] Wrapper for destination_point that accepts distance in meters."""
    # distance_nm = distance_m * PlannerConstants.METERS_TO_NM
    return destination_point(lat, lon, bearing_deg, distance_nm)

