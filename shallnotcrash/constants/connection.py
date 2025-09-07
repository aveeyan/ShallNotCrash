# shallnotcrash/constants/connection.py

class FGConnectionConstants:
    """Shared constants for FlightGear connections."""
    
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 5500
    DEFAULT_TELNET_CONFIG = f"socket,out,10,{DEFAULT_HOST},{DEFAULT_PORT},udp"