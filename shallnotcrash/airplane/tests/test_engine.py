#!/usr/bin/env python3
# shallnotcrash/airplane/tests/test_flight.py

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

# Add project root
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from shallnotcrash.airplane.systems.engine import EngineSystem

class TestEngineSystem(unittest.TestCase):
    def setUp(self):
        self.mock_fg = MagicMock()
        self.engine_system = EngineSystem(self.mock_fg)
        self.default_response = {'success': True, 'data': {'value': 2000.0}}
        self.mock_fg.get.return_value = self.default_response

    def test_engine_status_normal(self):
        result = self.engine_system.update()
        self.assertEqual(result['rpm'], 2000.0)
        self.assertEqual(result['status'], 'RUNNING')

    def test_engine_stopped(self):
        def side_effect(prop):
            if 'rpm' in prop:
                return {'success': True, 'data': {'value': 0}}
            return self.default_response
        self.mock_fg.get.side_effect = side_effect
        result = self.engine_system.update()
        self.assertEqual(result['status'], 'STOPPED')

    def test_engine_error(self):
        self.mock_fg.get.return_value = {'success': False, 'message': 'Sensor fail'}
        result = self.engine_system.update()
        self.assertEqual(result['status'], 'ERROR')
        self.assertIn('error', result)

if __name__ == '__main__':
    unittest.main()