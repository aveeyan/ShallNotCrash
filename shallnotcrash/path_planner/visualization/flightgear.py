# shallnotcrash/path_planner/visualization/flightgear.py
"""
Handles the real-time visualization of the flight path within FlightGear
by injecting "Corona" checkpoint models.
"""
from ..data_models import FlightPath
from ...fg_interface.core import FGInterface

class FlightGearVisualizer:
    """Injects and manages checkpoint models in the simulator."""

    def __init__(self, fg_interface: FGInterface):
        self.fg = fg_interface
        self.checkpoint_model_path = "Models/Geometry/corona.ac" # Example path

    def send_checkpoints_to_fg(self, path: FlightPath):
        """
        Clears old checkpoints and sends new ones to FlightGear via Nasal commands
        over the Telnet interface.
        """
        print(f"FLIGHTGEAR VIS: Sending {len(path.waypoints)} checkpoints to simulator.")
        # 1. Connect to Telnet if not connected.
        # 2. Send Nasal command to clear existing checkpoints.
        # 3. Loop through waypoints and send Nasal command to add each new one.
        pass

    def clear_checkpoints(self):
        """Sends a command to FlightGear to remove all checkpoints."""
        print("FLIGHTGEAR VIS: Clearing all checkpoints.")
        pass