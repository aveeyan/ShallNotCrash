# In shallnotcrash/fg_interface/core.py

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
        # ... (this method remains unchanged)
        try:
            self._protocol = TelnetProtocol(self.host, self.port)
            return self._format_response(
                success=True,
                message=f"Connected to FlightGear via Telnet ({self.host}:{self.port})",
                data={"protocol": "telnet", "host": self.host, "port": self.port}
            )
        except Exception as e:
            # ... (error handling remains unchanged)
            return self._format_response(
                success=False, message=str(e),
                data={"error_type": type(e).__name__, "host": self.host, "port": self.port}
            )

    # --- PROPOSED NEW METHOD ---
    def disconnect(self):
        """Closes the connection gracefully."""
        if self._protocol:
            self._protocol.close()
            self._protocol = None
            print("Socket connection closed.")
    
    def get(self, property_path: str) -> Dict[str, Any]:
        """Standardized JSON response for property requests."""
        # ... (this method remains unchanged, but benefits from the robust parsing)
        if not self._protocol:
            return self._format_response(success=False, message="Not connected")
        
        try:
            value = self._protocol.get(property_path)
            return self._format_response(
                success=True, message=f"Read {property_path}",
                data={"property": property_path, "value": value}
            )
        except Exception as e:
            return self._format_response(
                success=False, message=f"Failed to read {property_path}",
                data={"property": property_path, "error_details": str(e)}
            )

    # --- PROPOSED NEW METHOD ---
    def set(self, property_path: str, value: Any) -> Dict[str, Any]:
        """Writes a property and returns a standardized JSON response."""
        if not self._protocol:
            return self._format_response(success=False, message="Not connected")

        try:
            self._protocol.set(property_path, value)
            return self._format_response(
                success=True,
                message=f"Set {property_path} to {value}",
                data={"property": property_path, "value": value}
            )
        except Exception as e:
            return self._format_response(
                success=False,
                message=f"Failed to set {property_path}",
                data={"property": property_path, "error_details": str(e)}
            )
    
    def _format_response(self, success: bool, message: str, data: Dict = None) -> Dict[str, Any]:
        """Standardized response format for all methods."""
        # ... (this method remains unchanged)
        return {
            "module": "fg_interface", "success": success, "message": message,
            "data": data or {}, "timestamp": time.time()
        }
    
    # ... (the _get_unit helper method can be removed or kept, it's not critical path)
