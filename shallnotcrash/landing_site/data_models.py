# shallnotcrash/landing_site/data_models.py
"""
[REFACTORED - V2]
Defines the core data structures used throughout the landing site detection module.
V2 adds the 'Runway' dataclass to serve as a structured intermediate object
for data parsed from external sources, ensuring type safety and consistency.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple

# --- [NEW] Intermediate Data Structure for Parsed Runways ---
@dataclass
class Runway:
    """
    Represents a raw runway parsed from a data source like OSM. This is an
    intermediate object used for evaluation before being converted into a
    final LandingSite object. It holds the raw data in a structured format.
    """
    id: int
    nodes: List[int]
    tags: Dict[str, Any]
    node_coords: List[Tuple[float, float]] = field(default_factory=list)
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None

# --- Core Operational Data Structures ---

@dataclass
class Airport:
    """A simple data structure to hold airport or search origin information."""
    lat: float
    lon: float
    name: str

@dataclass
class SafetyReport:
    """Contains the detailed results of a safety analysis for a site."""
    is_safe: bool
    risk_level: str
    safety_score: int
    obstacle_count: int
    closest_civilian_distance_km: float
    civilian_violations: List[Dict] = field(default_factory=list)

@dataclass
class LandingSite:
    """Represents a single potential landing site with all its attributes."""
    lat: float
    lon: float
    length_m: float
    width_m: float
    site_type: str
    surface_type: str
    suitability_score: int
    distance_km: float
    safety_report: SafetyReport
    polygon_coords: List[tuple]
    orientation_degrees: float = 0.0
    elevation_m: Optional[int] = None

@dataclass
class SearchConfig:
    """Configuration parameters for a landing site search."""
    search_radius_km: int = 40
    max_sites_return: int = 15
    query_timeout: int = 180
    cache_enabled: bool = True
    civilian_exclusion_radius_m: int = 500
    max_slope_degrees: float = 2.0
    aircraft_profiles: Dict[str, Dict] = field(default_factory=lambda: {
        "cessna_172p": {"min_length_m": 400, "min_width_m": 8}
    })

    def get_profile_for(self, aircraft_type: str) -> Dict:
        return self.aircraft_profiles.get(aircraft_type, self.aircraft_profiles["cessna_172p"])

@dataclass
class SearchResults:
    """The final output object containing all results and metadata from a search."""
    origin_airport: Airport
    landing_sites: List[LandingSite]
    search_parameters: Dict[str, Any]
    analysis_summary: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
