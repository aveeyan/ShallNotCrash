# shallnotcrash/landing_site/utils/constants.py
"""
Static constants used throughout the landing site detection module.
Includes scoring weights, site classifiers, and safety definitions.
"""

class SiteConstants:
    """Constants used throughout the detector"""
    
    SCORING_WEIGHTS = {
        'airport': 100, 'airfield': 95, 'runway': 90, 'military_airfield': 85,
        # --- ENHANCEMENT: Added more granular types to catch all strips ---
        'airstrip': 80, 'landing_strip': 80, 'helipad': 75, 'grass_runway': 70, 
        'highway_straight': 65, 'race_track': 60, 'open_field_large': 55, 
        'golf_course_fairway': 50, 'agricultural_field': 45
    }
    
    SITE_CLASSIFIERS = {
        'priority_aviation': {
            ('aeroway', 'runway'): 'runway', ('aeroway', 'airfield'): 'airfield',
            # --- ENHANCEMENT: Expanded list to include more OSM tags for airstrips ---
            ('aeroway', 'airstrip'): 'airstrip', ('aeroway', 'landing_strip'): 'landing_strip',
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