# shallnotcrash/path_planner/data_models.py
"""
Defines the core, immutable data structures for the Path Planner.
"""
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class AircraftState:
    """Represents the complete state of the aircraft at a moment in time."""
    lat: float
    lon: float
    alt_ft: float
    heading_deg: float
    airspeed_kts: float

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
