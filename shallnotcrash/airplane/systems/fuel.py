# shallnotcrash/airplane/systems/fuel.py

from ..constants import C172PConstants

class FuelSystem:
    """Monitors C172P fuel state (2 tanks)"""
    
    def __init__(self, fg_connection):
        """
        Args:
            fg_connection: Connected FGInterface instance
        """
        self.fg = fg_connection
        self.const = C172PConstants
    
    def update(self) -> dict:
        """Returns current fuel state with status"""
        try:
            left_gal = self._get_tank_quantity(tank_idx=0)
            right_gal = self._get_tank_quantity(tank_idx=1)
            
            return {
                'tanks': {
                    'left': {'gallons': left_gal, 'lbs': left_gal * self.const.FUEL['DENSITY_PPG']},
                    'right': {'gallons': right_gal, 'lbs': right_gal * self.const.FUEL['DENSITY_PPG']}
                },
                'total_gal': left_gal + right_gal,
                'status': self._check_status(left_gal, right_gal),
                'is_usable': (left_gal + right_gal) <= self.const.FUEL['USABLE_CAPACITY_GAL']
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