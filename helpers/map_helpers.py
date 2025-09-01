import os
import json
import logging

def _modify_safety_score(site: dict) -> dict:
    """
    [NEW] Adjusts the safety score for certain site types to ensure they are
    not unfairly penalized. A runway, for example, should always be
    considered a high-safety option.
    """
    # Make a copy to avoid modifying the original data structure
    safety_report = site.get('safety_report', {}).copy()
    original_score = safety_report.get('safety_score', 0)
    site_type = site.get('site_type', 'Unknown')

    modified_score = original_score
    
    # --- The Modifier Logic ---
    if site_type == 'runway':
        # If a runway's calculated score is below 85, boost it to 85.
        # This guarantees it's always considered 'lime' or 'dark green'.
        if original_score < 85:
            modified_score = 85
            # Add a flag for traceability, which can be useful for debugging
            safety_report['was_modified'] = True 
            
    safety_report['safety_score'] = modified_score
    return safety_report


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
    [UPGRADED] Loads landing sites, modifies scores for safety, calculates a 
    priority score, and assigns a display color.
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

        # --- [STEP 1] Apply the safety score modifier ---
        modified_safety_report = _modify_safety_score(site)
        safety_score = modified_safety_report.get('safety_score', 0)
        
        # --- [STEP 2] Calculate Priority Score using the (potentially modified) safety score ---
        site_type = site.get('site_type', 'Unknown')
        
        priority_bonus = 0
        if site_type == 'runway':
            priority_bonus = 200
        elif site_type == 'road':
            priority_bonus = 100
        priority_score = safety_score + priority_bonus

        # --- [STEP 3] Determine color from the (potentially modified) safety score ---
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
                # Pass the modified report so the frontend shows the adjusted score
                "safety_report": modified_safety_report,
                "priority_score": priority_score,
                "display_color": display_color
            }
        }
        features.append(feature)

    return {"type": "FeatureCollection", "features": features}
