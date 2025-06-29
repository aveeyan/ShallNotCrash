import time
from typing import Dict, Any
from ..constants import C172PConstants
from ..exceptions import EngineException

class EngineSystem:
    """Monitors the Lycoming O-320-D2J engine in Cessna 172P.
    
    Key Metrics:
        - RPM, EGT, CHT, Oil Temp/Pressure, Fuel Flow
    Alerts:
        - Over/under RPM, Overheat, Low oil pressure, Fuel flow anomalies
    """

    def __init__(self, fg_connection):
        self.fg = fg_connection
        self.const = C172PConstants
        self._last_oil_change_hours = 0  # Track maintenance

    def update(self) -> Dict[str, Any]:
        """Returns complete engine status with safety checks."""
        try:
            # Primary metrics
            rpm = self._get_prop('RPM')
            egt = self._get_prop('EGT_F')
            cht = self._get_prop('CHT_F')
            oil_temp = self._get_prop('OIL_TEMP_F')
            oil_pressure = self._get_prop('OIL_PRESS_PSI')
            fuel_flow = self._get_prop('FUEL_FLOW_GPH')

            # Secondary calculations
            status = self._check_status(
                rpm, egt, cht, oil_temp, oil_pressure, fuel_flow
            )
            
            return {
                # Raw values
                'rpm': rpm,
                'egt': egt,
                'cht': cht,
                'oil_temp': oil_temp,
                'oil_pressure': oil_pressure,
                'fuel_flow': fuel_flow,
                
                # Derived states
                'status': status,
                'maintenance': self._get_maintenance_status(),
                
                # Operational limits
                'limits': {
                    'max_rpm': self.const.ENGINE['MAX_RPM'],
                    'redline_rpm': self.const.ENGINE['REDLINE_RPM'],
                    'max_egt': self.const.ENGINE['MAX_EGT'],
                    'max_cht': 500,  # Lycoming manual recommends < 500°F
                }
            }
            
        except Exception as e:
            raise EngineException(f"Engine monitoring failed: {str(e)}")

    def _get_prop(self, prop_key: str) -> float:
        """Fetches a property from FlightGear."""
        prop_path = getattr(self.const.PROPERTIES.ENGINE, prop_key)
        response = self.fg.get(prop_path)
        if not response['success']:
            raise ValueError(f"Failed to read {prop_key}: {response.get('message', 'No error details')}")
        return float(response['data']['value'])

    def _check_status(
        self, rpm: float, egt: float, cht: float, 
        oil_temp: float, oil_pressure: float, fuel_flow: float
    ) -> str:
        """Determines engine health state."""
        # Critical failures (immediate action required)
        if rpm <= 0:
            return 'ENGINE_FAILURE'
        elif oil_pressure < 10:  # Minimum psi at idle
            return 'OIL_PRESSURE_CRITICAL'
        elif cht > 500:  # Lycoming max
            return 'CHT_OVERHEAT'
        
        # Warning conditions (caution advised)
        elif rpm > self.const.ENGINE['REDLINE_RPM']:
            return 'OVERSPEED'
        elif egt > self.const.ENGINE['MAX_EGT']:
            return 'EGT_OVERHEAT'
        elif oil_temp > 245:  # Lycoming limit
            return 'OIL_OVERHEAT'
        elif fuel_flow < 2.0:  # ~Minimum GPH at idle
            return 'LOW_FUEL_FLOW'
            
        return 'NORMAL'

    def _get_maintenance_status(self) -> Dict[str, Any]:
        """Tracks engine time since last maintenance."""
        return {
            'hours_since_oil_change': self._last_oil_change_hours,
            'next_oil_change_due': max(0, 50 - self._last_oil_change_hours)  # 50-hour interval
        }