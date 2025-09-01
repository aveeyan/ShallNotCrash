# helpers/map_helpers.py
import os
import json
import logging

def get_color_from_score(score: int) -> str:
    """Returns a color hex code based on a safety score."""
    if score > 90:
        return "#006400"  # Dark Green
    elif score > 80:
        return "#32CD32"  # Lime Green
    elif score > 70:
        return "#FFFF00"  # Yellow
    elif score > 60:
        return "#FFA500"  # Orange
    else:
        return "#FF0000"  # Red

def load_sites_as_geojson(cache_path: str) -> dict:
    """
    [UPGRADED] Loads landing sites, calculates a priority score for sorting,
    and assigns a display color based on the safety score.
    """
    if not os.path.exists(cache_path):
        logging.error(f"Cache file not found at {cache_path}.")
        return {"type": "FeatureCollection", "features": []}

    try:
        with open(cache_path, 'r') as f:
            sites_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Error reading or parsing cache file {cache_path}: {e}")
        return {"type": "FeatureCollection", "features": []}

    features = []
    site_counter = 0
    for site in sites_data:
        site_counter += 1
        if 'polygon_coords' not in site or not site['polygon_coords']:
            continue

        # --- [NEW] Calculate Priority Score ---
        safety_score = site.get('safety_report', {}).get('safety_score', 0)
        site_type = site.get('site_type', 'Unknown')
        
        priority_bonus = 0
        if site_type == 'runway':
            priority_bonus = 200
        elif site_type == 'road':
            priority_bonus = 100
        priority_score = safety_score + priority_bonus

        # --- [NEW] Determine color from score ---
        display_color = get_color_from_score(safety_score)

        coords = [[lon, lat] for lat, lon in site['polygon_coords']]
        if coords[0] != coords[-1]:
            coords.append(coords[0])
            
        site_name = site.get('name')
        if not site_name:
            site_type_str = site.get('site_type', 'Site').replace('_', ' ').title()
            site_name = f"{site_type_str} #{site_counter}"

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            },
            "properties": {
                "name": site_name,
                "type": site_type,
                "score": site.get('suitability_score', 0),
                "length_m": site.get('length_m', 0),
                "heading": site.get('orientation_degrees', 0),
                "surface": site.get('surface_type', 'Unknown'),
                "center_lat": site.get('lat'),
                "center_lon": site.get('lon'),
                "safety_report": site.get('safety_report', {}),
                # --- [MODIFIED] Add new calculated properties ---
                "priority_score": priority_score,
                "display_color": display_color
            }
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}
