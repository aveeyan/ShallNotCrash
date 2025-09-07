# shallnotcrash/path_planner/data_models.py
"""
[UNIFIED - V3]
Defines the core data structures, now fully aligned with the rest of the
application. The redundant 'Runway' and 'SafetyReport' models have been
removed to rely on the canonical versions from the 'landing_site' package.
"""
from dataclasses import dataclass, field
from typing import List, Optional

# Import the canonical SafetyReport model to ensure type consistency
from shallnotcrash.landing_site.data_models import SafetyReport

@dataclass(frozen=True)
class AircraftState:
    """Represents the complete state of the aircraft at a moment in time."""
    lat: float
    lon: float
    alt_ft: float
    heading_deg: float
    airspeed_kts: float

# [REMOVED] The local 'Runway' dataclass is deleted. The system now uses
# 'LandingSite' from shallnotcrash.landing_site.data_models.

@dataclass
class Waypoint:
    """Represents a single point in a flight path."""
    lat: float
    lon: float
    alt_ft: float
    airspeed_kts: float
    notes: Optional[str] = None

# In shallnotcrash/path_planner/data_models.py

@dataclass
class FlightPath:
    """Represents a complete, flyable path from start to finish."""
    waypoints: List[Waypoint]
    total_distance_nm: float
    estimated_time_min: float

    # [THE FIX] Add the missing field back to the data model.
    emergency_profile: str

    safety_report: Optional[SafetyReport] = None # Uses canonical SafetyReport
# [REMOVED] The local 'SafetyReport' dataclass is deleted.
