# shallnotcrash/path_planner/core.py
"""
[RE-ARCHITECTED - V4 - COMPLETE]
This module contains the core logic for the path planner and guidance computer.

This version provides a complete implementation for FlightPath object creation,
resolving a critical TypeError by calculating and passing all required metadata.
"""
import logging
import math
from typing import List, Optional

from .data_models import AircraftState, Runway, Waypoint, FlightPath
# --- [FIX] Import the necessary calculation utility ---
from .utils.calculations import calculate_final_approach_path, calculate_path_distance
from .utils.coordinates import haversine_distance_nm

class PathPlanner:
    """
    Generates a complete flight path from an aircraft's current state to the
    best available runway.
    """
    def __init__(self, available_runways: List[Runway]):
        self.available_runways = available_runways
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(f"PathPlanner initialized with {len(available_runways)} available runways.")

    def generate_path(self, aircraft_state: AircraftState) -> Optional[FlightPath]:
        """
        Selects the best runway and generates a full flight path object to it,
        including all required metadata.
        """
        if not self.available_runways:
            logging.error("No runways available to plan a path.")
            return None

        best_runway = self._select_best_runway(aircraft_state)
        if not best_runway:
            logging.error("Could not select a suitable runway from the available options.")
            return None
        
        logging.info(f"Selected best runway: {best_runway.name} at {haversine_distance_nm(aircraft_state.lat, aircraft_state.lon, best_runway.center_lat, best_runway.center_lon):.2f} NM away.")

        waypoints = self._create_simplified_path(aircraft_state, best_runway)
        
        # --- [THE FIX] ---
        # Calculate the required metadata for the FlightPath object.
        total_distance = calculate_path_distance(waypoints)
        
        # Estimate time: Time (hr) = Distance (NM) / Speed (knots). Convert to minutes.
        # Use a non-zero average speed to avoid division by zero.
        avg_speed = aircraft_state.airspeed_kts if aircraft_state.airspeed_kts > 0 else 60.0
        estimated_time = (total_distance / avg_speed) * 60 if total_distance > 0 else 0.0

        # Create the object with ALL required arguments.
        return FlightPath(
            waypoints=waypoints,
            total_distance_nm=total_distance,
            estimated_time_min=estimated_time,
            emergency_profile="Simplified Glide/Approach"
        )

    def _select_best_runway(self, aircraft_state: AircraftState) -> Optional[Runway]:
        """Selects the closest runway from the available list."""
        # This logic remains correct.
        closest_runway = None
        min_dist = float('inf')
        for runway in self.available_runways:
            dist = haversine_distance_nm(
                aircraft_state.lat, aircraft_state.lon,
                runway.center_lat, runway.center_lon
            )
            if dist < min_dist:
                min_dist = dist
                closest_runway = runway
        return closest_runway

    def _create_simplified_path(self, aircraft_state: AircraftState, runway: Runway) -> List[Waypoint]:
        """Creates a basic path: Current -> FAF -> Threshold."""
        # This logic remains correct.
        logging.info("Generating simplified flight path...")
        faf_lat, faf_lon, threshold_lat, threshold_lon = calculate_final_approach_path(runway, final_approach_nm=3.0)
        wp1 = Waypoint(lat=aircraft_state.lat, lon=aircraft_state.lon, alt_ft=aircraft_state.alt_ft, airspeed_kts=aircraft_state.airspeed_kts)
        wp_faf = Waypoint(lat=faf_lat, lon=faf_lon, alt_ft=1500, airspeed_kts=80)
        wp_threshold = Waypoint(lat=threshold_lat, lon=threshold_lon, alt_ft=50, airspeed_kts=65)
        logging.info(f"Path created: Current -> FAF ({wp_faf.lat:.4f}, {wp_faf.lon:.4f}) -> Threshold ({wp_threshold.lat:.4f}, {wp_threshold.lon:.4f})")
        return [wp1, wp_faf, wp_threshold]

class GuidanceComputer:
    """
    Consumes a FlightPath and provides real-time target waypoints.
    """
    # This class is correct and requires no changes.
    def __init__(self):
        self.flight_path: Optional[FlightPath] = None
        self.current_waypoint_index: int = 0
        self.waypoint_capture_radius_nm: float = 0.5
        logging.info("GuidanceComputer initialized.")

    def load_new_path(self, flight_path: FlightPath):
        self.flight_path = flight_path
        self.current_waypoint_index = 0
        logging.info(f"New flight path loaded with {len(flight_path.waypoints)} waypoints.")

    def update_and_get_target(self, aircraft_state: AircraftState) -> Optional[Waypoint]:
        if not self.flight_path or self.current_waypoint_index >= len(self.flight_path.waypoints):
            return None
        target_waypoint = self.flight_path.waypoints[self.current_waypoint_index]
        distance_to_target = haversine_distance_nm(aircraft_state.lat, aircraft_state.lon, target_waypoint.lat, target_waypoint.lon)
        if distance_to_target < self.waypoint_capture_radius_nm:
            logging.info(f"Waypoint {self.current_waypoint_index} captured. Advancing to next.")
            self.current_waypoint_index += 1
            if self.current_waypoint_index >= len(self.flight_path.waypoints):
                logging.info("Final waypoint reached.")
                return None
        return self.flight_path.waypoints[self.current_waypoint_index]
