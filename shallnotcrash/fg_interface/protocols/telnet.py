"""shallnotcrash/fg_interface/protocols/telnet.py"""

import socket
from ..exceptions import FGCommError

class TelnetProtocol:
    """Handles low-level Telnet communication with FlightGear."""
    
    def __init__(self, host: str, port: int):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
    
    def get(self, property_path: str) -> str:
        """Sends 'get <property>' and returns the value."""
        cmd = f"get {property_path}\r\n".encode()
        self.socket.settimeout(2.0)
        self.socket.send(cmd)
        return self._parse_response(self.socket.recv(1024).decode())
    
    def _parse_response(self, response: str) -> float:
        """Extracts the numeric value from FlightGear's response."""
        try:
            return float(response.strip().split("'")[1])
        except (IndexError, ValueError) as e:
            raise FGCommError(f"Failed to parse response: {response}") from e