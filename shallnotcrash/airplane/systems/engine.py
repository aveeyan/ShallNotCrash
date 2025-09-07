import time
import random
from typing import Dict, Any
from ..constants import C172PConstants
from ..exceptions import EngineException

class EngineSystem:
    """Monitors the Lycoming O-320-D2J engine in Cessna 172P with vibration simulation."""
    
    def __init__(self, fg_connection):
        self.fg = fg_connection
        self.const = C172PConstants
        self._last_oil_change_hours = 0  # Track maintenance
        self._vibration_history = []  # For temporal analysis
        self._last_vibration_update = 0
        
    # ADD THIS METHOD
    def _get_prop(self, prop_key: str) -> float:
        prop_path = getattr(self.const.PROPERTIES.ENGINE, prop_key)
        response = self.fg.get(prop_path)
        if not response['success']:
            raise ValueError(f"Failed to read {prop_key}: {response.get('message', 'No error details')}")
        return float(response['data']['value'])
    
    def update(self) -> Dict[str, Any]:
        """Returns complete engine status with vibration simulation."""
        try:
            # Primary metrics
            rpm = self._get_prop('RPM')
            egt = self._get_prop('EGT_F')
            cht = self._get_prop('CHT_F')
            oil_temp = self._get_prop('OIL_TEMP_F')
            oil_pressure = self._get_prop('OIL_PRESS_PSI')
            fuel_flow = self._get_prop('FUEL_FLOW_GPH')
            
            # Calculate vibration
            vibration = self._calculate_vibration(rpm, oil_temp, oil_pressure)
            
            # Secondary calculations
            status = self._check_status(
                rpm, egt, cht, oil_temp, oil_pressure, fuel_flow, vibration
            )
            
            return {
                # Raw values
                'rpm': rpm,
                'egt': egt,
                'cht': cht,
                'oil_temp': oil_temp,
                'oil_pressure': oil_pressure,
                'fuel_flow': fuel_flow,
                'vibration': vibration,
                
                # Derived states
                'status': status,
                'maintenance': self._get_maintenance_status(),
                
                # Operational limits
                'limits': {
                    'max_rpm': self.const.ENGINE['MAX_RPM'],
                    'redline_rpm': self.const.ENGINE['REDLINE_RPM'],
                    'max_egt': self.const.ENGINE['MAX_EGT'],
                    'max_cht': 500,
                    'max_vibration': 10.0
                }
            }
            
        except Exception as e:
            raise EngineException(f"Engine monitoring failed: {str(e)}")

    def _calculate_vibration(self, rpm: float, oil_temp: float, oil_pressure: float) -> float:
        """Simulates engine vibration based on operational parameters"""
        # Base vibration increases with RPM
        rpm_factor = rpm / self.const.ENGINE['MAX_RPM']
        base_vibration = 0.5 + (rpm_factor * 4.0)
        
        # Oil temperature effect (higher temp = less viscosity = more vibration)
        temp_factor = max(0, (oil_temp - 180) / 100)  # Normalize 180-280°F
        temp_effect = temp_factor * 2.0
        
        # Oil pressure effect (low pressure = less damping = more vibration)
        pressure_factor = max(0, (50 - oil_pressure) / 30)  # Normalize 20-50 PSI
        pressure_effect = pressure_factor * 3.0
        
        # Engine harmonics effect (worst at certain RPM ranges)
        harmonic_factor = 0
        if 2000 < rpm < 2300:
            harmonic_factor = 1.5  # Harmonic vibration in cruise range
        elif rpm > 2500:
            harmonic_factor = 2.0  # High RPM vibration
            
        # Combine factors
        vibration = base_vibration + temp_effect + pressure_effect + harmonic_factor
        
        # Add random sensor noise
        vibration += random.uniform(-0.2, 0.2)
        
        # Maintain within realistic limits
        return max(0, min(10.0, vibration))

    def _check_status(
        self, rpm: float, egt: float, cht: float, 
        oil_temp: float, oil_pressure: float, 
        fuel_flow: float, vibration: float
    ) -> str:
        """Determines engine health state with vibration checks."""
        # Critical failures
        if rpm <= 0:
            return 'ENGINE_FAILURE'
        elif oil_pressure < 10:
            return 'OIL_PRESSURE_CRITICAL'
        elif cht > 500:
            return 'CHT_OVERHEAT'
        elif vibration > 8.0:
            return 'EXCESSIVE_VIBRATION'
            
        # Warning conditions
        elif rpm > self.const.ENGINE['REDLINE_RPM']:
            return 'OVERSPEED'
        elif egt > self.const.ENGINE['MAX_EGT']:
            return 'EGT_OVERHEAT'
        elif oil_temp > 245:
            return 'OIL_OVERHEAT'
        elif fuel_flow < 2.0:
            return 'LOW_FUEL_FLOW'
        elif vibration > 5.0:
            return 'HIGH_VIBRATION'
            
        return 'NORMAL'

    def _get_maintenance_status(self) -> Dict[str, Any]:
        """Tracks engine time since last maintenance."""
        return {
            'hours_since_oil_change': self._last_oil_change_hours,
            'next_oil_change_due': max(0, 50 - self._last_oil_change_hours)  # 50-hour interval
        }