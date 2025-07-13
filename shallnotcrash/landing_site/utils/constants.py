# shallnotcrash/path_planner/utils/constants.py
"""
Static constants used throughout the landing site detection module.
Includes scoring weights, site classifiers, and safety definitions.
"""

class SiteConstants:
    """Constants used throughout the detector"""
    
    # Scoring weights for different site types
    SCORING_WEIGHTS = {
        'airport': 100, 'airfield': 95, 'runway': 90, 'military_airfield': 85,
        # --- ENHANCEMENT: Added new site type for smaller strips ---
        'airstrip': 80, 'helipad': 75, 'grass_runway': 70, 'highway_straight': 65,
        'race_track': 60, 'open_field_large': 55, 'golf_course_fairway': 50,
        'agricultural_field': 45
    }
    
    # Site classification mappings from OSM tags
    SITE_CLASSIFIERS = {
        'priority_aviation': {
            ('aeroway', 'runway'): 'runway', ('aeroway', 'airfield'): 'airfield',
            # --- ENHANCEMENT: Added 'airstrip' to find smaller sites like Arnarvollur ---
            ('aeroway', 'airstrip'): 'airstrip',
            ('aeroway', 'aerodrome'): 'airport', ('landuse', 'airport'): 'airport',
            ('military', 'airfield'): 'military_airfield', ('aeroway', 'helipad'): 'helipad'
        },
        'suitable_surfaces': {
            ('highway', 'motorway'): 'highway_straight', ('highway', 'trunk'): 'highway_straight',
            ('leisure', 'track'): 'race_track', ('sport', 'motor'): 'race_track',
            ('leisure', 'golf_course'): 'golf_course_fairway', ('landuse', 'grass'): 'open_field_large',
            ('landuse', 'meadow'): 'open_field_large', ('landuse', 'farmland'): 'agricultural_field'
        }
    }
    
    # --- ENHANCEMENT: Refined obstacle definitions for stricter safety checks ---
    OBSTACLES = {
        'structures': {'building', 'house', 'apartments', 'school', 'hospital', 'church', 'retail', 'commercial', 'industrial', 'tower', 'mast', 'chimney', 'silo', 'bunker', 'bridge'},
        'vegetation': {'forest', 'wood', 'trees', 'scrub'},
        'infrastructure': {'power_line', 'railway', 'fence', 'wall'},
        'water': {'river', 'lake', 'reservoir', 'pond', 'stream'}
    }
    
    # Surface type bonuses for scoring
    SURFACE_BONUSES = {
        'paved': 15, 'asphalt': 15, 'concrete': 20, 'grass': 10,
        'gravel': 5, 'dirt': 0, 'sand': -5
    }