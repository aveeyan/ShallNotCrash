# shallnotcrash/path_planner/utils/coordinates.py
"""
A collection of geodetic calculation utilities for working with
latitude and longitude coordinates.
"""

import math

def get_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates the initial bearing from point 1 to point 2.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees).
        lat2, lon2: Latitude and longitude of point 2 (in degrees).

    Returns:
        float: The bearing in degrees (from 0 to 360).
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlon = lon2_rad - lon1_rad

    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    
    bearing_rad = math.atan2(y, x)
    
    # Convert bearing from radians to degrees and normalize
    return (math.degrees(bearing_rad) + 360) % 360

def get_midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """
    Calculates the midpoint between two coordinates.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees).
        lat2, lon2: Latitude and longitude of point 2 (in degrees).

    Returns:
        A tuple containing (latitude, longitude) of the midpoint.
    """
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
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

def get_destination_point(lat: float, lon: float, bearing_deg: float, distance_m: float) -> tuple[float, float]:
    """
    Calculates the destination point given a starting point, bearing, and distance.

    Args:
        lat, lon: Starting latitude and longitude (in degrees).
        bearing_deg: Bearing (in degrees).
        distance_m: Distance to travel (in meters).

    Returns:
        A tuple containing (destination_latitude, destination_longitude).
    """
    R = 6371000  # Earth radius in meters
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)

    lat_dest_rad = math.asin(
        math.sin(lat_rad) * math.cos(distance_m / R) +
        math.cos(lat_rad) * math.sin(distance_m / R) * math.cos(bearing_rad)
    )

    lon_dest_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(distance_m / R) * math.cos(lat_rad),
        math.cos(distance_m / R) - math.sin(lat_rad) * math.sin(lat_dest_rad)
    )

    return math.degrees(lat_dest_rad), math.degrees(lon_dest_rad)
