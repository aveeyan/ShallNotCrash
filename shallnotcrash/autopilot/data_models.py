# In shallnotcrash/autopilot/data_models.py

from dataclasses import dataclass, field
from typing import List

@dataclass
class AutopilotState:
    """
    Represents the aircraft's current state, read from the simulator.
    """
    lat: float          # Current latitude in degrees
    lon: float          # Current longitude in degrees
    alt_ft: float       # Current altitude in feet above sea level
    heading_deg: float  # Current magnetic heading in degrees
    roll_deg: float     # Current bank angle in degrees (positive = right bank)
    pitch_deg: float    # Current pitch angle in degrees (positive = nose up)
    airspeed_kts: float # Current airspeed in knots

@dataclass
class ControlOutput:
    """
    Represents the calculated control surface commands.
    Values are typically normalized from -1.0 to 1.0.
    """
    aileron_cmd: float  # Aileron command (-1.0 for full left, 1.0 for full right)
    elevator_cmd: float # Elevator command (-1.0 for nose down, 1.0 for nose up)
    rudder_cmd: float   # Rudder command (-1.0 for left, 1.0 for right)
    throttle_cmd: float = 0.0

# --- MISSING DATACLASSES ADDED BELOW ---

@dataclass
class Waypoint:
    """
    Defines a single point in the flight path with target parameters.
    """
    lat: float
    lon: float
    alt_ft: float
    airspeed_kts: float

@dataclass
class FlightPath:
    """
    Represents the entire sequence of waypoints to be followed.
    """
    waypoints: List[Waypoint] = field(default_factory=list)
