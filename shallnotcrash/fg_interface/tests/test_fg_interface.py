# shallnotcrash/fg_interface/tests/test_fg_interface.py

import unittest
from unittest.mock import patch, MagicMock
import socket
import time
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Now import the modules using absolute imports
from shallnotcrash.fg_interface.core import FGConnection
from shallnotcrash.fg_interface.exceptions import FGCommError
from shallnotcrash.fg_interface.protocols.telnet import TelnetProtocol

class TestFGConnection(unittest.TestCase):
    """Test cases for FGConnection class"""
    
    def setUp(self):
        self.conn = FGConnection(host="localhost", port=5500)
        
    @patch.object(TelnetProtocol, '__init__', return_value=None)
    @patch.object(TelnetProtocol, 'get')
    def test_successful_connection(self, mock_get, mock_init):
        """Test successful FlightGear connection"""
        response = self.conn.connect()
        
        self.assertTrue(response['success'])
        self.assertEqual(response['module'], 'fg_interface')
        self.assertEqual(response['data']['protocol'], 'telnet')
        mock_init.assert_called_once_with("localhost", 5500)

    @patch.object(TelnetProtocol, '__init__', side_effect=socket.error("Connection refused"))
    def test_connection_refused(self, mock_init):
        """Test connection refused error"""
        response = self.conn.connect()
        
        self.assertFalse(response['success'])
        self.assertEqual(response['data']['error_type'], 'ConnectionRefusedError')
        self.assertIn("--telnet=socket", response['data']['solution'])

    @patch.object(TelnetProtocol, '__init__', side_effect=Exception("Generic error"))
    def test_generic_connection_error(self, mock_init):
        """Test generic connection error"""
        response = self.conn.connect()
        
        self.assertFalse(response['success'])
        self.assertEqual(response['data']['error_type'], 'Exception')

    @patch.object(TelnetProtocol, 'get', return_value="1234.56")
    def test_successful_property_read(self, mock_get):
        """Test successful property read"""
        self.conn._protocol = TelnetProtocol("localhost", 5500)
        response = self.conn.get("/position/altitude-ft")
        
        self.assertTrue(response['success'])
        self.assertEqual(response['data']['value'], 1234.56)
        mock_get.assert_called_once_with("/position/altitude-ft")

    @patch.object(TelnetProtocol, 'get', side_effect=FGCommError("Invalid property"))
    def test_invalid_property_read(self, mock_get):
        """Test invalid property read"""
        self.conn._protocol = TelnetProtocol("localhost", 5500)
        response = self.conn.get("/invalid/property")
        
        self.assertFalse(response['success'])
        self.assertEqual(response['data']['error_type'], 'FGCommError')

    def test_property_read_without_connection(self):
        """Test property read without establishing connection"""
        response = self.conn.get("/position/altitude-ft")
        
        self.assertFalse(response['success'])
        self.assertEqual(response['data']['required_action'], 'Call connect() first')

    @patch.object(TelnetProtocol, 'get', return_value="'invalid_response'")
    def test_malformed_response_handling(self, mock_get):
        """Test handling of malformed FlightGear responses"""
        self.conn._protocol = TelnetProtocol("localhost", 5500)
        response = self.conn.get("/position/altitude-ft")
        
        self.assertFalse(response['success'])
        self.assertEqual(response['data']['error_type'], 'ValueError')

class TestTelnetProtocol(unittest.TestCase):
    """Test cases for TelnetProtocol implementation"""
    
    def setUp(self):
        self.patcher = patch('socket.socket')
        self.mock_socket = self.patcher.start()
        self.socket_instance = MagicMock()
        self.mock_socket.return_value = self.socket_instance
        
    def tearDown(self):
        self.patcher.stop()
        
    def test_protocol_initialization(self):
        """Test Telnet protocol initialization"""
        protocol = TelnetProtocol("localhost", 5500)
        self.mock_socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_instance.connect.assert_called_once_with(("localhost", 5500))

    def test_successful_property_read(self):
        """Test successful property read via telnet"""
        self.socket_instance.recv.return_value = b"123.45 '4567.89'\r\n"
        protocol = TelnetProtocol("localhost", 5500)
        result = protocol.get("/position/altitude-ft")
        
        self.assertEqual(result, 4567.89)
        self.socket_instance.send.assert_called_once_with(b"get /position/altitude-ft\r\n")

    def test_malformed_response(self):
        """Test malformed telnet response"""
        self.socket_instance.recv.return_value = b"invalid response"
        protocol = TelnetProtocol("localhost", 5500)
        
        with self.assertRaises(FGCommError):
            protocol.get("/position/altitude-ft")

    def test_connection_error(self):
        """Test connection error during property read"""
        self.socket_instance.send.side_effect = socket.error("Connection failed")
        protocol = TelnetProtocol("localhost", 5500)
        
        with self.assertRaises(FGCommError):
            protocol.get("/position/altitude-ft")

if __name__ == '__main__':
    unittest.main()