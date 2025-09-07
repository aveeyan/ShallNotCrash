# shallnotcrash/random_flight/config.py

class RandomFlightConfig:
    """Configuration for random flight generation."""
    
    # Default values
    DEFAULT_AIRCRAFT = "c172p"
    DEFAULT_AIRPORT = "BIKF"
    MIN_DISTANCE_NM = 5
    MAX_DISTANCE_NM = 20
    MIN_ALTITUDE_FT = 3000
    MAX_ALTITUDE_FT = 10000
    DEFAULT_HEADING = None 
    DEFAULT_SPEED_KTS = 90
    
    # Time of day options
    TIME_OPTIONS = ['dawn', 'morning', 'noon', 'afternoon', 'dusk', 'night']
    DEFAULT_TIME = TIME_OPTIONS[1]