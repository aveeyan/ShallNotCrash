# shallnotcrash/random_flight/core.py

# Standard Libraries
import time
from typing import Dict, Any, Optional

# Local Imports
from .config import RandomFlightConfig
from .exceptions import RandomFlightError
from .generators.position import PositionGenerator
from ..constants.connection import FGConnectionConstants

class RandomFlight:
    """Generates random C172P flights near BIKF with configurable parameters."""
    
    def __init__(self):
        self.position_gen = PositionGenerator()
        self.config = RandomFlightConfig()
    
    def generate(
        self,
        airport_icao: Optional[str] = None,
        distance_nm: Optional[float] = None,
        altitude_ft: Optional[float] = None,
        heading: Optional[float] = None
    ) -> Dict[str, Any]:
        """Generate random flight parameters."""
        try:
            airport = airport_icao or self.config.DEFAULT_AIRPORT
            position = self.position_gen.generate(
                distance_nm=distance_nm,
                altitude_ft=altitude_ft,
                heading=heading
            )
            
            return self._format_response(
                success=True,
                message=f"C172P flight generated near {airport}",
                data={
                    "aircraft": self.config.DEFAULT_AIRCRAFT,
                    "airport": airport,
                    "position": position,
                    "time_of_day": self.config.DEFAULT_TIME,
                    "fg_launch_command": self._generate_launch_command(airport, position)
                }
            )
        except Exception as e:
            return self._format_response(
                success=False,
                message=str(e),
                data={
                    "airport": airport_icao or self.config.DEFAULT_AIRPORT,
                    "error_type": type(e).__name__
                }
            )
    
    def _generate_launch_command(self, airport: str, position: Dict) -> str:
        """Generate FlightGear launch command with configured time."""
        return (
            f"fgfs --aircraft={self.config.DEFAULT_AIRCRAFT} "
            f"--airport={airport} "
            f"--offset-distance={position['distance_nm']} "
            f"--offset-azimuth={position['bearing']} "
            f"--altitude={position['altitude_ft']} "
            f"--heading={position['heading'] or position['bearing']} "
            f"--vc={position['speed_kt']} "
            f"--timeofday={self.config.DEFAULT_TIME} "
            f"--telnet={FGConnectionConstants.DEFAULT_TELNET_CONFIG}"
        )
    
    def _format_response(self, success: bool, message: str, data: Dict) -> Dict[str, Any]:
        """Standardized JSON response."""
        return {
            "module": "random_flight",
            "success": success,
            "message": message,
            "data": data,
            "timestamp": time.time()
        }