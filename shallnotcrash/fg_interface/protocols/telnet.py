# In shallnotcrash/fg_interface/protocols/telnet.py

import socket
from typing import Any
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

    # --- PROPOSED NEW METHOD ---
    def set(self, property_path: str, value: Any):
        """Sends 'set <property> <value>'."""
        cmd = f"set {property_path} {value}\r\n".encode()
        self.socket.settimeout(2.0)
        self.socket.send(cmd)
        # Note: For 'set', we often don't need to wait for a response,
        # but we could add a recv() here if we need to confirm the command was processed.
        # For now, we will send and continue.

    def _parse_response(self, response: str) -> float:
        """Extracts the numeric value from FlightGear's response."""
        try:
            # This parsing is very specific. Let's make it a bit more robust.
            # FG often returns "value (type)". We'll try to get the part before the space.
            cleaned_response = response.strip().split(" ")[0]
            return float(cleaned_response)
        except (IndexError, ValueError) as e:
            # If the above fails, fall back to your original parsing.
            try:
                return float(response.strip().split("'")[1])
            except (IndexError, ValueError):
                 raise FGCommError(f"Failed to parse response: {response}") from e

    def close(self):
        """Closes the socket connection."""
        self.socket.close()
        