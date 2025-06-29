# shallnotcrash/random_flight/exceptions.py

class RandomFlightError(Exception):
    """Base exception for random flight generation errors."""
    pass

class InvalidPositionError(RandomFlightError):
    """Raised when invalid position parameters are provided."""
    pass