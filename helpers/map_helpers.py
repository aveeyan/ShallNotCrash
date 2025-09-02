# helpers/map_helpers.py
import logging
from typing import List, Dict, Optional

# Path Planning Imports
from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState, Waypoint, FlightPath
from shallnotcrash.landing_site.data_models import LandingSite, SafetyReport

_planner_cache: Dict[str, PathPlanner] = {}

def get_color_from_score(score: int) -> str:
    if score > 90: return "#006400"  # Dark Green for excellent
    elif score > 80: return "#32CD32" # Lime Green for good
    elif score > 70: return "#FFFF00" # Yellow for okay
    elif score > 60: return "#FFA500" # Orange for marginal
    else: return "#FF0000"           # Red for poor

def load_sites_as_geojson(sites_as_dicts: List[dict]) -> dict:
    features = []
    for i, site in enumerate(sites_as_dicts):
        if 'polygon_coords' not in site or not site['polygon_coords']:
            continue
        
        safety_report = site.get('safety_report', {})
        safety_score = safety_report.get('safety_score', 0)
        
        site_type = site.get('site_type', 'Unknown')
        priority_bonus = 200 if 'runway' in site_type else 100 if 'road' in site_type else 0
        priority_score = safety_score + priority_bonus
        
        display_color = site.get('display_color') or get_color_from_score(safety_score)
        
        coords = [[lon, lat] for lat, lon in site['polygon_coords']]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
            
        site_name = site.get('name') or f"{site_type.replace('_', ' ').title()} #{i+1}"
        
        feature = {
            "type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": { "id": i, "name": site_name, "type": site_type, "length_m": site.get('length_m'), 
                           "center_lat": site.get('lat'), "center_lon": site.get('lon'), "safety_report": safety_report,
                           "priority_score": priority_score, "display_color": display_color }
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}

def _get_or_create_planner(terrain_analyzer, planner_id: str = "default") -> PathPlanner:
    if planner_id not in _planner_cache:
        _planner_cache[planner_id] = PathPlanner(terrain_analyzer=terrain_analyzer)
        logging.info(f"Created new PathPlanner instance: {planner_id}")
    return _planner_cache[planner_id]

def clear_planner_cache():
    global _planner_cache
    _planner_cache.clear()
    logging.info("Planner cache cleared.")

def generate_realtime_path(terrain_analyzer, sites_cache: List[dict], telemetry: dict, site_id: int):
    """
    [FIXED] This function is now synchronized with the new high-speed geometric planner
    in core.py.
    """
    try:
        site_dict = sites_cache[site_id]
        
        aircraft_state = AircraftState(
            lat=telemetry['lat'], lon=telemetry['lng'], alt_ft=telemetry['altitude'],
            heading_deg=telemetry['heading'], airspeed_kts=telemetry['speed']
        )
        
        planner = _get_or_create_planner(terrain_analyzer, str(site_id))
        landing_site = _dict_to_landing_site(site_dict)
        
        # [FIX] Call the main public method of the new geometric planner.
        # All the complex logic is now handled inside this single call.
        flight_path = planner.generate_path_to_site(aircraft_state, landing_site)
        
        if flight_path:
            waypoints_json = [[wp.lat, wp.lon] for wp in flight_path.waypoints]
            return {
                'waypoints': waypoints_json,
                'total_distance_nm': flight_path.total_distance_nm,
                'estimated_time_min': flight_path.estimated_time_min,
                'emergency_profile': flight_path.emergency_profile
            }

    except Exception as e:
        logging.error(f"Path planning failed for site_id {site_id}: {e}", exc_info=True)
    
    return None

def _dict_to_landing_site(site_dict: dict) -> LandingSite:
    """Convert a site dictionary back to a LandingSite object."""
    safety_report = None
    if 'safety_report' in site_dict and site_dict['safety_report']:
        sr_dict = site_dict['safety_report']
        safety_report = SafetyReport(
            is_safe=sr_dict.get('is_safe', True), risk_level=sr_dict.get('risk_level', 'UNKNOWN'),
            safety_score=sr_dict.get('safety_score', 0), obstacle_count=sr_dict.get('obstacle_count', 0),
            closest_civilian_distance_km=sr_dict.get('closest_civilian_distance_km', 999.0)
        )
    return LandingSite(
        lat=site_dict['lat'], lon=site_dict['lon'], length_m=site_dict.get('length_m', 0.0),
        width_m=site_dict.get('width_m', 0.0), site_type=site_dict['site_type'],
        surface_type=site_dict.get('surface_type', 'unknown'),
        suitability_score=site_dict.get('suitability_score', 0),
        distance_km=site_dict.get('distance_km', 0.0), safety_report=safety_report,
        polygon_coords=site_dict.get('polygon_coords', []),
        orientation_degrees=site_dict.get('orientation_degrees', 0.0),
        elevation_m=site_dict.get('elevation_m')
    )
