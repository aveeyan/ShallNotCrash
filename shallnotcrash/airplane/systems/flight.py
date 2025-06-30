# shallnotcrash/airplane/systems/flight.py

# Standard import
from typing import Dict, Any

# Local import
from ..constants import C172PConstants
from ..exceptions import FlightSystemException

class FlightSystem:
    """Monitors flight dynamics (position, orientation, speed)"""

    def __init__(self, fg_connection):
        """
        Args:
            fg_connection: Connected FGInterface instance
        """
        self.fg = fg_connection
        self.const = C172PConstants

    def update(self) -> Dict[str, Any]:
        """Returns current flight state"""
        try:
            # Position
            latitude = self._get('LATITUDE')
            longitude = self._get('LONGITUDE')
            altitude_ft = self._get('ALTITUDE_FT')
            agl_ft = self._get('ALTITUDE_AGL_FT')
            ground_elev = self._get('GROUND_ELEV_FT')

            # Attitude
            pitch_deg = self._get('PITCH_DEG')
            roll_deg = self._get('ROLL_DEG')
            heading_deg = self._get('HEADING_DEG')

            # Speed
            airspeed_kt = self._get('AIRSPEED_KT')
            vertical_speed_fps = self._get('VERTICAL_SPEED_FPS')

            return {
                'position': {
                    'latitude_deg': latitude,
                    'longitude_deg': longitude,
                    'altitude_ft': altitude_ft,
                    'agl_ft': agl_ft,
                    'ground_elev_ft': ground_elev
                },
                'attitude': {
                    'pitch_deg': pitch_deg,
                    'roll_deg': roll_deg,
                    'heading_deg': heading_deg
                },
                'speed': {
                    'airspeed_kt': airspeed_kt,
                    'vertical_speed_fps': vertical_speed_fps
                },
                'status': self._check_status(airspeed_kt, pitch_deg, roll_deg)
            }

        except Exception as e:
            raise FlightSystemException(f"Flight system error: {str(e)}")

    def _get(self, key: str) -> float:
        """Fetches a flight property from FlightGear"""
        prop_path = getattr(self.const.PROPERTIES.FLIGHT, key)
        response = self.fg.get(prop_path)
        if not response['success']:
            raise ValueError(f"Failed to read {key}: {response.get('message', 'No details')}")
        return float(response['data']['value'])

    def _check_status(self, airspeed: float, pitch: float, roll: float) -> str:
        """Determines flight status based on thresholds"""
        if airspeed < self.const.SPEEDS['VS0']:
            return "STALL_WARNING"
        if abs(pitch) > 30:
            return "HIGH_PITCH"
        if abs(roll) > 45:
            return "HIGH_ROLL"
        return "NORMAL"
