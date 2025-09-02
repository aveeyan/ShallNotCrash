# helpers/map_helpers.py
import logging
from typing import List, Dict, Optional

# Path Planning Imports
from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState, Waypoint
from shallnotcrash.landing_site.data_models import LandingSite, SafetyReport

# [NEW] Global planner cache to maintain runway selection across requests
_planner_cache: Dict[str, PathPlanner] = {}

def _modify_safety_score(site: dict) -> dict:
    safety_report = site.get('safety_report', {}).copy()
    original_score = safety_report.get('safety_score', 0)
    site_type = site.get('site_type', 'Unknown')
    if site_type == 'runway' and original_score < 85:
        safety_report['safety_score'] = 85
        safety_report['was_modified'] = True
    return safety_report

def get_color_from_score(score: int) -> str:
    if score > 90: return "#006400"
    elif score > 80: return "#32CD32"
    elif score > 70: return "#FFFF00"
    elif score > 60: return "#FFA500"
    else: return "#FF0000"

def load_sites_as_geojson(sites_as_dicts: List[dict]) -> dict:
    features = []
    for i, site in enumerate(sites_as_dicts):
        if 'polygon_coords' not in site or not site['polygon_coords']:
            continue
        modified_safety_report = _modify_safety_score(site)
        safety_score = modified_safety_report.get('safety_score', 0)
        site_type = site.get('site_type', 'Unknown')
        priority_bonus = 0
        if site_type == 'runway': priority_bonus = 200
        elif site_type == 'road': priority_bonus = 100
        priority_score = safety_score + priority_bonus
        display_color = get_color_from_score(safety_score)
        coords = [[lon, lat] for lat, lon in site['polygon_coords']]
        if coords and coords[0] != coords[-1]: coords.append(coords[0])
        site_name = site.get('name') or f"{site.get('site_type', 'Site').replace('_', ' ').title()} #{i+1}"
        feature = {
            "type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {
                "id": i, "name": site_name, "type": site.get('site_type'),
                "length_m": site.get('length_m'), "center_lat": site.get('lat'),
                "center_lon": site.get('lon'), "safety_report": modified_safety_report,
                "priority_score": priority_score, "display_color": display_color
            }
        }
        features.append(feature)
    return {"type": "FeatureCollection", "features": features}

def _get_or_create_planner(terrain_analyzer, planner_id: str = "default") -> PathPlanner:
    """Get cached planner or create a new one. This maintains runway selection state."""
    if planner_id not in _planner_cache:
        _planner_cache[planner_id] = PathPlanner(terrain_analyzer=terrain_analyzer)
        logging.info(f"Created new PathPlanner instance: {planner_id}")
    return _planner_cache[planner_id]

def clear_planner_cache():
    """Clear all cached planners. Useful when terrain analyzer changes."""
    global _planner_cache
    for planner in _planner_cache.values():
        if hasattr(planner, 'clear_runway_cache'):
            planner.clear_runway_cache()
    _planner_cache.clear()
    logging.info("Planner cache cleared.")

def generate_realtime_path(terrain_analyzer, sites_cache: List[dict], telemetry: dict, site_id: int, use_smart_caching: bool = True):
    """
    Generate a path with optional smart caching.
    
    Args:
        use_smart_caching: If True, uses the enhanced planner with runway selection caching.
                          If False, falls back to precomputed approach method.
    """
    try:
        site_dict = sites_cache[site_id]
        
        # Create the AircraftState object
        aircraft_state = AircraftState(
            lat=telemetry['lat'], lon=telemetry['lng'], alt_ft=telemetry['altitude'],
            heading_deg=telemetry['heading'], airspeed_kts=telemetry['speed']
        )
        
        if use_smart_caching:
            # [NEW] Use the enhanced planner with runway caching
            logging.info(f"Generating smart-cached path to site {site_id}")
            
            # Convert site_dict back to LandingSite object for the enhanced planner
            landing_site = _dict_to_landing_site(site_dict)
            
            # Get cached planner (maintains runway selection state)
            planner = _get_or_create_planner(terrain_analyzer, f"site_{site_id}")
            
            # Generate path using the enhanced algorithm
            flight_path = planner.generate_path_to_site(aircraft_state, landing_site)
            
        else:
            # [FALLBACK] Use the original precomputed method for maximum speed
            logging.info(f"Generating precomputed path to site {site_id}")
            
            # Check if the pre-computed data exists in the cache
            if 'precomputed_faf' not in site_dict or 'precomputed_threshold' not in site_dict:
                logging.error(f"Site ID {site_id} is missing pre-computed approach data. Please regenerate the cache.")
                return None

            # Re-hydrate the pre-computed waypoints from the cache dictionary
            faf_waypoint = Waypoint(**site_dict['precomputed_faf'])
            threshold_waypoint = Waypoint(**site_dict['precomputed_threshold'])
            
            # Use a simple planner for precomputed paths
            planner = PathPlanner(terrain_analyzer=terrain_analyzer)
            flight_path = planner.generate_path_from_precomputed(
                aircraft_state, faf_waypoint, threshold_waypoint
            )
        
        if flight_path:
            waypoints_json = [[wp.lat, wp.lon] for wp in flight_path.waypoints]
            path_info = {
                'waypoints': waypoints_json,
                'total_distance_nm': flight_path.total_distance_nm,
                'estimated_time_min': flight_path.estimated_time_min,
                'emergency_profile': flight_path.emergency_profile
            }
            
            # Add runway selection info if available
            if hasattr(planner, '_cached_runway_selection') and planner._cached_runway_selection:
                _, _, approach_heading = planner._cached_runway_selection
                path_info['approach_heading'] = approach_heading
                path_info['runway_cached'] = True
            
            return path_info

    except IndexError:
        logging.error(f"Invalid site_id '{site_id}' requested for path planning.")
    except Exception as e:
        logging.error(f"Path planning failed: {e}", exc_info=True)
    
    return None

def _dict_to_landing_site(site_dict: dict) -> LandingSite:
    """Convert a site dictionary back to a LandingSite object."""
    safety_report = None
    if 'safety_report' in site_dict and site_dict['safety_report']:
        safety_report_dict = site_dict['safety_report']
        safety_report = SafetyReport(
            is_safe=safety_report_dict.get('is_safe', True),
            risk_level=safety_report_dict.get('risk_level', 'UNKNOWN'),
            safety_score=safety_report_dict.get('safety_score', 0),
            obstacle_count=safety_report_dict.get('obstacle_count', 0),
            closest_civilian_distance_km=safety_report_dict.get('closest_civilian_distance_km', 999.0)
        )
    
    return LandingSite(
        lat=site_dict['lat'],
        lon=site_dict['lon'],
        length_m=site_dict.get('length_m', 0.0),
        width_m=site_dict.get('width_m', 0.0),
        site_type=site_dict['site_type'],
        surface_type=site_dict.get('surface_type', 'unknown'),
        suitability_score=site_dict.get('suitability_score', 0),
        distance_km=site_dict.get('distance_km', 0.0),
        safety_report=safety_report,
        polygon_coords=site_dict.get('polygon_coords', []),
        orientation_degrees=site_dict.get('orientation_degrees', 0.0),
        elevation_m=site_dict.get('elevation_m')
    )
