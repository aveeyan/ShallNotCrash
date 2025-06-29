#!/usr/bin/env python3
# shallnotcrash/airplane/tests/test_fuel.py
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

import unittest
from unittest.mock import MagicMock
from shallnotcrash.airplane.systems.fuel import FuelSystem
from shallnotcrash.airplane.constants import C172PConstants

class TestFuelSystem(unittest.TestCase):
    def setUp(self):
        """Create a mock FGConnection and test instance"""
        self.mock_fg = MagicMock()
        self.fuel_system = FuelSystem(self.mock_fg)
        
        # Configure mock responses
        self.good_response = {
            'success': True,
            'data': {'value': 20.0}  # 20 gallons in each tank for normal case
        }
        self.error_response = {
            'success': False,
            'message': 'Simulated error'
        }

    def test_normal_fuel_state(self):
        """Test normal fuel conditions"""
        self.mock_fg.get.side_effect = [self.good_response, self.good_response]
        
        result = self.fuel_system.update()
        
        self.assertEqual(result['tanks']['left']['gallons'], 20.0)
        self.assertEqual(result['tanks']['right']['gallons'], 20.0)
        self.assertEqual(result['total_gal'], 40.0)
        self.assertEqual(result['status'], 'NORMAL')
        self.assertTrue(result['is_usable'])

    def test_low_fuel_warning(self):
        """Test low fuel warning threshold"""
        low_fuel_response = {'success': True, 'data': {'value': 4.0}}  # 4 gal per tank
        self.mock_fg.get.side_effect = [low_fuel_response, low_fuel_response]
        
        result = self.fuel_system.update()
        self.assertEqual(result['status'], 'LOW_FUEL')  # 8 gal total < 10 gal warning

    def test_critical_fuel(self):
        """Test critical fuel threshold"""
        crit_fuel_response = {'success': True, 'data': {'value': 2.0}}  # 2 gal per tank
        self.mock_fg.get.side_effect = [crit_fuel_response, crit_fuel_response]
        
        result = self.fuel_system.update()
        self.assertEqual(result['status'], 'CRITICAL')  # 4 gal total < 5 gal critical

    def test_fuel_imbalance(self):
        """Test fuel imbalance detection"""
        self.mock_fg.get.side_effect = [
            {'success': True, 'data': {'value': 25.0}},  # Left tank
            {'success': True, 'data': {'value': 15.0}}   # Right tank (10 gal difference)
        ]
        
        result = self.fuel_system.update()
        self.assertEqual(result['status'], 'IMBALANCE')

    def test_usable_capacity(self):
        """Test usable fuel capacity flag"""
        full_tank_response = {'success': True, 'data': {'value': 28.0}}  # Full tank
        self.mock_fg.get.side_effect = [full_tank_response, full_tank_response]
        
        result = self.fuel_system.update()
        self.assertFalse(result['is_usable'])  # 56 gal > 53 gal usable

    def test_error_handling(self):
        """Test failed fuel quantity read"""
        self.mock_fg.get.side_effect = [self.good_response, self.error_response]
        
        result = self.fuel_system.update()
        self.assertIn('error', result)
        self.assertEqual(result['status'], 'ERROR')

    def test_pounds_conversion(self):
        """Test gallons to pounds conversion"""
        self.mock_fg.get.side_effect = [self.good_response, self.good_response]
        
        result = self.fuel_system.update()
        self.assertAlmostEqual(
            result['tanks']['left']['lbs'],
            20.0 * C172PConstants.FUEL['DENSITY_PPG'],
            places=2
        )

if __name__ == '__main__':
    unittest.main()