# shallnotcrash/airplane/systems/fuel.py

import time
from ..constants import C172PConstants

class FuelSystem:
    """Monitors C172P fuel state (2 tanks) with flow and endurance calculations"""
    
    def __init__(self, fg_connection):
        """
        Args:
            fg_connection: Connected FGInterface instance
        """
        self.fg = fg_connection
        self.const = C172PConstants
        self.last_update = time.time()
        self.last_total_fuel = None
        
    def update(self) -> dict:
        """Returns current fuel state with status, flow, and endurance"""
        try:
            # Get current fuel quantities
            left_gal = self._get_tank_quantity(tank_idx=0)
            right_gal = self._get_tank_quantity(tank_idx=1)
            current_total = left_gal + right_gal
            current_time = time.time()
            
            # Initialize fuel flow and endurance
            fuel_flow_gph = 0.0
            endurance_min = 0
            
            # Calculate fuel flow if we have previous data
            if self.last_total_fuel is not None and current_time > self.last_update:
                time_diff = max(0.1, current_time - self.last_update)
                fuel_diff = self.last_total_fuel - current_total
                fuel_flow_gph = max(0.0, (fuel_diff / time_diff) * 3600)
                
                # Calculate endurance only when fuel flow is positive
                if fuel_flow_gph > 0:
                    endurance_min = (current_total / fuel_flow_gph) * 60
                    
            # Update state for next calculation
            self.last_total_fuel = current_total
            self.last_update = current_time
            
            return {
                'tanks': {
                    'left': {
                        'gallons': left_gal, 
                        'lbs': left_gal * self.const.FUEL['DENSITY_PPG']
                    },
                    'right': {
                        'gallons': right_gal, 
                        'lbs': right_gal * self.const.FUEL['DENSITY_PPG']
                    }
                },
                'total_gal': current_total,
                'fuel_flow': fuel_flow_gph,
                'endurance_min': endurance_min,
                'status': self._check_status(left_gal, right_gal),
                'is_usable': current_total <= self.const.FUEL['USABLE_CAPACITY_GAL']
            }
        except Exception as e:
            return {
                'error': str(e),
                'status': 'ERROR'
            }
    
    def _get_tank_quantity(self, tank_idx: int) -> float:
        """Get quantity for tank 0 (left) or 1 (right)"""
        prop = (
            self.const.PROPERTIES.FUEL.LEFT_QTY_GAL 
            if tank_idx == 0 
            else self.const.PROPERTIES.FUEL.RIGHT_QTY_GAL
        )
        response = self.fg.get(prop)
        if not response['success']:
            raise ValueError(f"Failed to read tank {tank_idx}: {response['message']}")
        return float(response['data']['value'])
    
    def _check_status(self, left_gal: float, right_gal: float) -> str:
        """Determine fuel system health"""
        total = left_gal + right_gal
        imbalance = abs(left_gal - right_gal)
        
        if total < self.const.FUEL['CRITICAL_THRESHOLD_GAL']:
            return 'CRITICAL'
        elif total < self.const.FUEL['WARNING_THRESHOLD_GAL']:
            return 'LOW_FUEL'
        elif imbalance > self.const.FUEL['MAX_IMBALANCE_GAL']:
            return 'IMBALANCE'
        return 'NORMAL'
