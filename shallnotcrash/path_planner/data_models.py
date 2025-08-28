# shallnotcrash/path_planner/data_models.py
"""
Defines the core, immutable data structures for the Path Planner.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from dataclasses import field

# --- Immutable Geographic and Aircraft Structures ---

@dataclass(frozen=True)
class AircraftState:
    """Represents the complete state of the aircraft at a moment in time."""
    lat: float
    lon: float
    alt_ft: float
    heading_deg: float
    airspeed_kts: float

@dataclass(frozen=True)
class Runway:
    """
    Represents the essential geometric properties of a runway for path planning.
    This is a simplified, immutable structure used internally by the PathPlanner.
    """
    name: str
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    center_lat: float
    center_lon: float
    bearing_deg: float
    length_m: float
    width_m: float
    surface_type: str
    # --- [CRITICAL CORRECTION] ---
    # These parameters MUST be optional to allow for simplified runway definitions
    # in simulations and loaders where this data may not be available.
    length_m: Optional[float] = None
    width_m: Optional[float] = None
    surface_type: Optional[str] = None

# --- Mutable Flight Plan Structures ---

@dataclass
class Waypoint:
    """Represents a single point in a flight path."""
    lat: float
    lon: float
    alt_ft: float
    airspeed_kts: float
    notes: Optional[str] = None

@dataclass
class FlightPath:
    """Represents a complete, flyable path from start to finish."""
    waypoints: List[Waypoint]
    total_distance_nm: float
    estimated_time_min: float
    emergency_profile: str
    safety_report: Optional['SafetyReport'] = None

# --- [NEW ADDITION] ---
@dataclass
class SafetyReport:
    """
    Represents the output of a terrain and safety analysis.
    This is the standard data contract for the TerrainAnalyzer.
    """
    is_safe: bool
    risk_level: str
    safety_score: int
    obstacle_count: int = 0
    closest_civilian_distance_km: Optional[float] = None
    civilian_violations: List[Dict[str, Any]] = field(default_factory=list)
