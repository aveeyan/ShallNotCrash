# shallnotcrash/airplane/core.py

import time
from typing import Dict, Any, List
from .constants import C172PConstants
from .systems.fuel import FuelSystem
from .systems.engine import EngineSystem
from .systems.flight import FlightSystem
from .exceptions import FlightSystemException, EngineException, FuelSystemException

class Cessna172P:
    """Main aircraft class for Cessna 172P monitoring"""
    
    def __init__(self, fg_connection):
        """
        Args:
            fg_connection: Connected FGInterface instance
        """
        self.fg = fg_connection
        self.const = C172PConstants
        self._systems = {
            'fuel': FuelSystem(fg_connection),
            'engine': EngineSystem(fg_connection),
            'flight': FlightSystem(fg_connection)
        }
        self._last_update = 0
        
    def get_telemetry(self) -> Dict[str, Any]:
        """Get current aircraft state with timestamp"""
        try:
            self._last_update = time.time()
            telemetry = {
                'timestamp': self._last_update,
                'fuel': self._get_fuel_status(),
                'engine': self._get_engine_status(),
                'flight': self._get_flight_status()
            }
            telemetry['alerts'] = self._check_cross_system_alerts(telemetry)
            return telemetry
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': self._last_update
            }
    
    def _get_fuel_status(self) -> Dict[str, Any]:
        """Get fuel system state with error handling"""
        try:
            return self._systems['fuel'].update()
        except Exception as e:
            raise FuelSystemException(f"Fuel system error: {str(e)}") from e
    
    def _get_engine_status(self) -> Dict[str, Any]:
        """Get engine state with error handling"""
        try:
            return self._systems['engine'].update()
        except Exception as e:
            raise EngineException(
                f"Engine monitoring failed: {str(e)}", 
                severity="CRITICAL" if "FAILURE" in str(e) else "WARNING"
            ) from e
    
    def _get_flight_status(self) -> Dict[str, Any]:
        """Get flight state with error handling"""
        try:
            return self._systems['flight'].update()
        except Exception as e:
            raise FlightSystemException(f"Flight system error: {str(e)}") from e
    
    def _check_cross_system_alerts(self, status: Dict[str, Any]) -> List[str]:
        """Detect emergencies requiring multi-system awareness"""
        alerts = []
        if (status['fuel']['status'] == 'LOW_FUEL' and 
            status['engine']['rpm'] > self.const.ENGINE['REDLINE_RPM']):
            alerts.append("LOW_FUEL_WITH_HIGH_RPM")
            
        # Add more cross-checks as needed
        return alerts
