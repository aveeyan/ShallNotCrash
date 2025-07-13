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
        'helipad': 80, 'grass_runway': 75, 'highway_straight': 70, 'race_track': 65,
        'open_field_large': 60, 'golf_course_fairway': 55, 'agricultural_field': 50
    }
    
    # Site classification mappings from OSM tags
    SITE_CLASSIFIERS = {
        'priority_aviation': {
            ('aeroway', 'runway'): 'runway', ('aeroway', 'airfield'): 'airfield',
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
    
    # Civilian area definitions for safety analysis
    CIVILIAN_AREAS = {
        'high_priority': {'school', 'hospital', 'kindergarten', 'university', 'college', 'nursing_home'},
        'residential': {'residential', 'house', 'apartments', 'housing', 'suburb', 'village'},
        'commercial': {'commercial', 'retail', 'industrial', 'warehouse', 'factory', 'office'}
    }
    
    # Obstacle definitions
    OBSTACLES = {
        'vegetation': {'forest', 'wood', 'trees', 'scrub'},
        'structures': {'tower', 'mast', 'chimney', 'silo', 'building'},
        'infrastructure': {'power_line', 'railway', 'bridge'},
        'water': {'river', 'lake', 'reservoir', 'pond'}
    }
    
    # Surface type bonuses for scoring
    SURFACE_BONUSES = {
        'paved': 15, 'asphalt': 15, 'concrete': 20, 'grass': 10,
        'gravel': 5, 'dirt': 0, 'sand': -5
    }