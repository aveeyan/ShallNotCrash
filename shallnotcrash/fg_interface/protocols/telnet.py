# In shallnotcrash/fg_interface/protocols/telnet.py

import socket
from typing import Any
from ..exceptions import FGCommError

class TelnetProtocol:
    """Handles low-level Telnet communication with FlightGear."""
    
    # [MODIFICATION 1] Add 'timeout' parameter with a default value
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # [MODIFICATION 2] Set the timeout BEFORE connecting
        self.socket.settimeout(timeout)
        
        # Now, the connect call will respect the timeout
        self.socket.connect((host, port))
        
        # Store the timeout for later use in get/set
        self.timeout = timeout
    
    def get(self, property_path: str) -> str:
        """Sends 'get <property>' and returns the value."""
        cmd = f"get {property_path}\r\n".encode()
        # [MODIFICATION 3] Use the stored timeout value for consistency
        self.socket.settimeout(self.timeout) 
        self.socket.send(cmd)
        return self._parse_response(self.socket.recv(1024).decode())

    def set(self, property_path: str, value: Any):
        """Sends 'set <property> <value>'."""
        cmd = f"set {property_path} {value}\r\n".encode()
        # [MODIFICATION 4] Use the stored timeout value here as well
        self.socket.settimeout(self.timeout)
        self.socket.send(cmd)

    def _parse_response(self, response: str) -> float:
        # This parsing logic is good and does not need to be changed.
        try:
            cleaned_response = response.strip().split(" ")[0]
            return float(cleaned_response)
        except (IndexError, ValueError) as e:
            try:
                return float(response.strip().split("'")[1])
            except (IndexError, ValueError):
                 raise FGCommError(f"Failed to parse response: {response}") from e

    def close(self):
        """Closes the socket connection."""
        self.socket.close()
