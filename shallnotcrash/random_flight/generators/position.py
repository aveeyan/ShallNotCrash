# shallnotcrash/random_flight/generators/position.py

# Standard Libraries
import random
from typing import Dict, Optional

# Local Imports
from ..config import RandomFlightConfig

class PositionGenerator:
    """Generates random position parameters for C172P."""
    
    def __init__(self):
        self.config = RandomFlightConfig()
    
    def generate(
        self,
        distance_nm: Optional[float] = None,
        altitude_ft: Optional[float] = None,
        heading: Optional[float] = None
    ) -> Dict[str, float]:
        """Generate position with configurable parameters."""
        return {
            "distance_nm": distance_nm or random.uniform(
                self.config.MIN_DISTANCE_NM,
                self.config.MAX_DISTANCE_NM
            ),
            "bearing": random.uniform(0, 359),
            "altitude_ft": altitude_ft or random.randint(
                self.config.MIN_ALTITUDE_FT,
                self.config.MAX_ALTITUDE_FT
            ),
            "heading": heading,
            "speed_kt": self.config.DEFAULT_SPEED_KTS
        }