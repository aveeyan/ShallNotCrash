# helpers/map_helpers.py
import logging
from typing import List

# Path Planning Imports
from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState, Waypoint
from shallnotcrash.landing_site.data_models import LandingSite, SafetyReport

def _modify_safety_score(site: dict) -> dict:
    # ... (function is unchanged) ...
    safety_report = site.get('safety_report', {}).copy()
    original_score = safety_report.get('safety_score', 0)
    site_type = site.get('site_type', 'Unknown')
    if site_type == 'runway' and original_score < 85:
        safety_report['safety_score'] = 85
        safety_report['was_modified'] = True
    return safety_report

def get_color_from_score(score: int) -> str:
    # ... (function is unchanged) ...
    if score > 90: return "#006400"
    elif score > 80: return "#32CD32"
    elif score > 70: return "#FFFF00"
    elif score > 60: return "#FFA500"
    else: return "#FF0000"

def load_sites_as_geojson(sites_as_dicts: List[dict]) -> dict:
    # ... (function is unchanged) ...
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

def generate_realtime_path(terrain_analyzer, sites_cache: List[dict], telemetry: dict, site_id: int):
    try:
        site_dict = sites_cache[site_id]
        
        # [THE FIX] Check if the pre-computed data exists in the cache
        if 'precomputed_faf' not in site_dict or 'precomputed_threshold' not in site_dict:
            logging.error(f"Site ID {site_id} is missing pre-computed approach data. Please regenerate the cache.")
            return None

        # Re-hydrate the pre-computed waypoints from the cache dictionary
        faf_waypoint = Waypoint(**site_dict['precomputed_faf'])
        threshold_waypoint = Waypoint(**site_dict['precomputed_threshold'])
        
        # Create the AircraftState object
        aircraft_state = AircraftState(
            lat=telemetry['lat'], lon=telemetry['lng'], alt_ft=telemetry['altitude'],
            heading_deg=telemetry['heading'], airspeed_kts=telemetry['speed']
        )
        
        # Initialize the PathPlanner
        planner = PathPlanner(terrain_analyzer=terrain_analyzer)
        
        # [MODIFIED] Call a new, faster method that uses the pre-computed data
        flight_path = planner.generate_path_from_precomputed(
            aircraft_state, faf_waypoint, threshold_waypoint
        )
        
        if flight_path:
            waypoints_json = [[wp.lat, wp.lon] for wp in flight_path.waypoints]
            return {'waypoints': waypoints_json}

    except IndexError:
        logging.error(f"Invalid site_id '{site_id}' requested for path planning.")
    except Exception as e:
        logging.error(f"Path planning failed: {e}", exc_info=True)
    
    return None
