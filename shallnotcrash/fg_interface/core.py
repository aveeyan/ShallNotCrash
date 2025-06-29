"""shallnotcrash/fg_interface/core.py"""

import json
from typing import Dict, Any
import time

from .protocols.telnet import TelnetProtocol
from .exceptions import FGCommError
from ..constants.flightgear import FGProps
from ..constants.connection import FGConnectionConstants

# Constants
DEFAULT_HOST = FGConnectionConstants.DEFAULT_HOST
DEFAULT_PORT = FGConnectionConstants.DEFAULT_PORT

class FGConnection:
    """Handles FlightGear communication with a JSON interface."""
    
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._protocol = None
    
    def connect(self) -> Dict[str, Any]:
        """Returns a standardized JSON response for both success and failure."""
        try:
            self._protocol = TelnetProtocol(self.host, self.port)
            return self._format_response(
                success=True,
                message=f"Connected to FlightGear via Telnet ({self.host}:{self.port})",
                data={
                    "protocol": "telnet",
                    "host": self.host,
                    "port": self.port
                }
            )
        except ConnectionRefusedError as e:
            return self._format_response(
                success=False,
                message="Connection refused - Is FlightGear running with --telnet option?",
                data={
                    "error_type": "ConnectionRefusedError",
                    "host": self.host,
                    "port": self.port,
                    "solution": "Start FlightGear with: --telnet=socket,out,10,localhost,5500,udp"
                }
            )
        except Exception as e:
            return self._format_response(
                success=False,
                message=str(e),
                data={
                    "error_type": type(e).__name__,
                    "host": self.host,
                    "port": self.port
                }
            )
    
    def get(self, property_path: str) -> Dict[str, Any]:
        """Standardized JSON response for property requests."""
        if not self._protocol:
            return self._format_response(
                success=False,
                message="Not connected to FlightGear",
                data={
                    "required_action": "Call connect() first"
                }
            )
        
        try:
            value = self._protocol.get(property_path)
            return self._format_response(
                success=True,
                message=f"Read {property_path}",
                data={
                    "property": property_path,
                    "value": value,
                    "unit": self._get_unit(property_path)  # Optional helper method
                }
            )
        except Exception as e:
            return self._format_response(
                success=False,
                message=f"Failed to read {property_path}",
                data={
                    "property": property_path,
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                }
            )
    
    def _format_response(self, success: bool, message: str, data: Dict) -> Dict[str, Any]:
        """Standardized response format for all methods."""
        return {
            "module": "fg_interface",
            "success": success,
            "message": message,
            "data": data,
            "timestamp": time.time()
        }
    
    def _get_unit(self, property_path: str) -> str:
        """Helper to infer units from property path (optional)"""
        if "altitude" in property_path:
            return "ft"
        if "airspeed" in property_path:
            return "kt"
        if "latitude" or "longitude" in property_path:
            return "deg"
        return "unknown"