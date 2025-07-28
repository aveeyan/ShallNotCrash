# shallnotcrash/path_planner/data_models.py
"""
Defines the core data structures used for flight path planning.
"""
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True, eq=True)
class AircraftState:
    """
    Represents a complete, hashable state of the aircraft at a point in space and time.
    Used as a node in the A* search graph. 'frozen=True' makes it hashable.
    """
    lat: float
    lon: float
    alt_ft: float
    airspeed_kts: float
    heading_deg: float

    def __hash__(self):
        """
        Custom hash to handle floating point inaccuracies by rounding.
        This is crucial for using the state in dictionaries and sets (A* closed set).
        """
        return hash((
            round(self.lat, 4),
            round(self.lon, 4),
            int(self.alt_ft),
            int(self.airspeed_kts)
        ))

@dataclass
class Waypoint:
    """
    Represents a single point in the generated flight path. This is a simpler
    version of AircraftState, intended for the final output path.
    """
    lat: float
    lon: float
    alt_ft: float
    airspeed_kts: float
    notes: Optional[str] = None

@dataclass
class FlightPath:
    """
    Represents the complete, final flight path solution.
    """
    waypoints: List[Waypoint]
    total_distance_nm: float
    estimated_time_min: float
    emergency_profile: str
    is_viable: bool = True