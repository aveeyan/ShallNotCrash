class AircraftException(Exception):
    """Base exception for all aircraft-related errors"""
    pass

class FuelSystemException(AircraftException):
    """Fuel system specific failures"""
    pass

class EngineException(AircraftException):
    """Engine monitoring failures with severity levels"""
    def __init__(self, message: str, severity: str = "WARNING"):
        """
        Args:
            severity: "WARNING"|"CRITICAL"|"EMERGENCY"
        """
        self.severity = severity
        super().__init__(message)

class FlightSystemException(AircraftException):
    """Flight state monitoring errors"""
    pass

class SensorException(AircraftException):
    """Failed sensor readings"""
    pass