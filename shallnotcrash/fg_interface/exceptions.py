"""shallnotcrash/fg_interface/exceptions.py"""

class FGCommError(Exception):
    """Base exception for all FlightGear communication errors."""
    pass

class ConnectionTimeout(FGCommError):
    """Raised when FlightGear doesn't respond."""
    pass

class ProtocolError(FGCommError):
    """Raised for malformed FlightGear responses."""
    pass