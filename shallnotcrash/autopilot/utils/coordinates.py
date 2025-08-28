# In autopilot/utils/coordinates.py

import math

def get_bearing_and_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """
    Calculates the initial bearing and haversine distance between two points.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees).
        lat2, lon2: Latitude and longitude of point 2 (in degrees).

    Returns:
        A tuple containing:
        - Bearing (in degrees, from 0 to 360).
        - Distance (in nautical miles).
    """
    # Earth radius in nautical miles
    R = 3440.065

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # --- Haversine formula for distance ---
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_nm = R * c

    # --- Formula for bearing ---
    y = math.sin(dlon) * math.cos(lat2_rad)
    x = math.cos(lat1_rad) * math.sin(lat2_rad) - \
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    bearing_rad = math.atan2(y, x)
    
    # Convert bearing from radians to degrees and normalize
    bearing_deg = (math.degrees(bearing_rad) + 360) % 360

    return bearing_deg, distance_nm