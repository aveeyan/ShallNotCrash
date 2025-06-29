#!/usr/bin/env python3
# shallnotcrash/airplane/tests/test_flight.py

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

# Add project root
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from shallnotcrash.airplane.systems.flight import FlightSystem
from shallnotcrash.airplane.constants import C172PConstants

class TestFlightSystem(unittest.TestCase):
    def setUp(self):
        self.mock_fg = MagicMock()
        self.flight_system = FlightSystem(self.mock_fg)

        self.mock_fg.get.return_value = {'success': True, 'data': {'value': 100.0}}

    def test_basic_flight_data(self):
        result = self.flight_system.update()
        self.assertIn('position', result)
        self.assertIn('attitude', result)
        self.assertIn('speed', result)
        self.assertEqual(result['status'], 'NORMAL')

    def test_high_pitch_warning(self):
        self.mock_fg.get.side_effect = [
            {'success': True, 'data': {'value': 0}},  # LAT
            {'success': True, 'data': {'value': 0}},  # LON
            {'success': True, 'data': {'value': 100}},
            {'success': True, 'data': {'value': 90}},
            {'success': True, 'data': {'value': 10}},
            {'success': True, 'data': {'value': 35}},  # Pitch
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 100}},
            {'success': True, 'data': {'value': 0}}
        ]
        result = self.flight_system.update()
        self.assertEqual(result['status'], 'HIGH_PITCH')

    def test_high_roll_warning(self):
        self.mock_fg.get.side_effect = [
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 100}},
            {'success': True, 'data': {'value': 90}},
            {'success': True, 'data': {'value': 10}},
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 60}},  # Roll
            {'success': True, 'data': {'value': 100}},
            {'success': True, 'data': {'value': 0}}
        ]
        result = self.flight_system.update()
        self.assertEqual(result['status'], 'HIGH_ROLL')

    def test_stall_warning(self):
        self.mock_fg.get.side_effect = [
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 100}},
            {'success': True, 'data': {'value': 90}},
            {'success': True, 'data': {'value': 10}},
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 0}},
            {'success': True, 'data': {'value': 30}},  # Airspeed below VS0
            {'success': True, 'data': {'value': 0}}
        ]
        result = self.flight_system.update()
        self.assertEqual(result['status'], 'STALL_WARNING')

    def test_error_response(self):
        self.mock_fg.get.return_value = {'success': False, 'message': 'Sim error'}
        with self.assertRaises(Exception):
            self.flight_system.update()
