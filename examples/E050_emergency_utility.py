#!/usr/bin/env python3
# shallnotcrash/examples/E050_emergency_utility.py

import time
from pathlib import Path
import sys
from collections import deque
from typing import Dict, Any, Optional

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.airplane.core import Cessna172P
from shallnotcrash.emergency.utilities import FlightPhase
from shallnotcrash.emergency.utilities import (
    detect_anomalies,
    analyze_system_correlations,
)
from shallnotcrash.emergency.protocols import (
    detect_engine_failure,
    detect_fuel_emergency,
    detect_structural_failure
)

# Constants
VIBRATION_WARNING = 5.0
VIBRATION_CRITICAL = 8.0
VIBRATION_HISTORY_SIZE = 10
UPDATE_INTERVAL = 5  # seconds
DEFAULT_FLIGHT_PHASE = FlightPhase.CRUISE

class VibrationMonitor:
    """Tracks and analyzes engine vibration patterns"""
    def __init__(self):
        self.history = deque(maxlen=VIBRATION_HISTORY_SIZE)
        self.trend = 'stable'
        self.max_recent = 0.0
        
    def update(self, current: float) -> Dict[str, Any]:
        """Update vibration analysis with new reading"""
        self.history.append(current)
        self.max_recent = max(self.history) if self.history else 0.0
        
        if len(self.history) >= 2:
            if current > self.history[-2]:
                self.trend = 'increasing'
            elif current < self.history[-2]:
                self.trend = 'decreasing'
            else:
                self.trend = 'stable'
                
        return {
            'current': current,
            'average': sum(self.history)/len(self.history) if self.history else 0.0,
            'max_recent': self.max_recent,
            'trend': self.trend,
            'severity': self._assess_severity(current)
        }
    
    def _assess_severity(self, value: float) -> str:
        """Classify vibration severity level"""
        if value >= VIBRATION_CRITICAL:
            return 'CRITICAL'
        if value >= VIBRATION_WARNING:
            return 'WARNING'
        return 'NORMAL'

def determine_flight_phase(telemetry: Dict[str, Any]) -> FlightPhase:
    """Automatically determine current flight phase"""
    altitude = telemetry['altitude']
    vsi = telemetry['vsi']
    
    if altitude < 500:
        return FlightPhase.TAKEOFF if vsi > 0 else FlightPhase.LANDING
    elif vsi > 500:
        return FlightPhase.CLIMB
    elif vsi < -500:
        return FlightPhase.DESCENT
    return FlightPhase.CRUISE

def format_telemetry(aircraft_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw aircraft data to emergency detection format"""
    try:
        flight_data = aircraft_data['flight']
        return {
            # Engine parameters
            'rpm': aircraft_data['engine']['rpm'],
            'cht': aircraft_data['engine']['cht'],
            'oil_temp': aircraft_data['engine']['oil_temp'],
            'oil_press': aircraft_data['engine']['oil_pressure'],
            'fuel_flow': aircraft_data['engine']['fuel_flow'],
            'vibration': aircraft_data['engine']['vibration'],
            'engine_status': aircraft_data['engine']['status'],
            
            # Fuel system
            'fuel_left': aircraft_data['fuel']['tanks']['left']['gallons'],
            'fuel_right': aircraft_data['fuel']['tanks']['right']['gallons'],
            'total_fuel': aircraft_data['fuel']['total_gal'],
            'fuel_status': aircraft_data['fuel']['status'],
            
            # Flight dynamics
            'airspeed': flight_data['speed']['airspeed_kt'],
            'altitude': flight_data['position']['altitude_ft'],
            'vsi': flight_data['speed']['vertical_speed_fps'] * 60,
            'pitch': flight_data['attitude']['pitch_deg'],
            'roll': flight_data['attitude']['roll_deg'],
            'heading': flight_data['attitude']['heading_deg'],
            'flight_status': flight_data['status'],
            
            # Structural loads
            'g_load': flight_data.get('g_load', 1.0),
            'control_asymmetry': abs(flight_data['attitude']['pitch_deg']) + 
                                abs(flight_data['attitude']['roll_deg']) +
                                abs(flight_data['attitude']['heading_deg'] % 360 - 180)
        }
    except KeyError as e:
        raise ValueError(f"Missing telemetry data: {str(e)}")

def convert_diagnostic(diagnostic) -> Dict[str, Any]:
    """Convert diagnostic object to dictionary format"""
    if isinstance(diagnostic, dict):
        return diagnostic
    elif hasattr(diagnostic, '__dict__'):
        return vars(diagnostic)
    elif hasattr(diagnostic, 'to_dict'):
        return diagnostic.to_dict()
    return {'diagnostics': diagnostic}

def display_status(telemetry: Dict[str, Any], vibration: Dict[str, Any]):
    """Show current system status with visual indicators"""
    print("\n=== AIRCRAFT STATUS ===")
    print(f"ENGINE: {telemetry['engine_status']:12} RPM: {telemetry['rpm']:.0f}")
    print(f"FUEL:   {telemetry['fuel_status']:12} Total: {telemetry['total_fuel']:.1f} gal")
    print(f"FLIGHT: {telemetry['flight_status']:12} Alt: {telemetry['altitude']:.0f} ft")
    
    print("\n=== VIBRATION MONITOR ===")
    vib_bar = "█" * min(10, int(telemetry['vibration']))
    print(f"Level: {vib_bar} {telemetry['vibration']:.1f}/10.0 ({vibration['severity']})")
    print(f"Trend: {vibration['trend'].upper():10} Max Recent: {vibration['max_recent']:.1f}")
    
    if vibration['severity'] == 'CRITICAL':
        print("\n\x1b[31m! CRITICAL VIBRATION - IMMEDIATE ACTION REQUIRED !\x1b[0m")
    elif vibration['severity'] == 'WARNING':
        print("\n\x1b[33m! WARNING - HIGH VIBRATION DETECTED !\x1b[0m")

def display_anomalies(anomaly_scores: Dict[str, Any]):
    """Highlight significant anomalies"""
    print("\n=== ANOMALY DETECTION ===")
    for param, score in anomaly_scores.items():
        # Check if score has normalized_score attribute (new) or z_score attribute (old)
        score_value = getattr(score, 'normalized_score', getattr(score, 'z_score', 0))
        is_anomaly = getattr(score, 'is_anomaly', False)
        
        if is_anomaly or param in ['vibration', 'oil_press', 'oil_temp']:
            color = "\x1b[31m" if is_anomaly else "\x1b[33m"
            print(f"{color}{param.upper():15} Score: {score_value:5.2f} {'(ALERT)' if is_anomaly else ''}\x1b[0m")

def display_recommendations(vibration: Dict[str, Any], correlations: Dict[str, float]):
    """Provide actionable maintenance recommendations"""
    print("\n=== RECOMMENDED ACTIONS ===")
    
    if vibration['severity'] == 'CRITICAL':
        print("- \x1b[31mREDUCE POWER IMMEDIATELY\x1b[0m")
        print("- Land at nearest suitable airport")
        print("- Inspect engine mounts and propeller balance")
    elif vibration['severity'] == 'WARNING':
        print("- Reduce power to lower vibration levels")
        print("- Monitor engine parameters closely")
        print("- Check for loose components")
    
    if correlations.get('engine-structural', 0) > 0.7:
        print("- Inspect engine mounts and airframe connections")
    if correlations.get('engine-fuel', 0) > 0.7:
        print("- Check fuel lines and pumps for vibration damage")

def main():
    print("\n=== FLIGHTGEAR EMERGENCY MONITOR ===")
    print(f"Vibration Thresholds: Warning {VIBRATION_WARNING}, Critical {VIBRATION_CRITICAL}")
    
    # Initialize systems
    fg = FGConnection()
    if not fg.connect()['success']:
        print("Failed to connect to FlightGear")
        return
    
    aircraft = Cessna172P(fg)
    vibration_monitor = VibrationMonitor()
    
    try:
        while True:
            # Get and format telemetry
            raw_data = aircraft.get_telemetry()
            telemetry = format_telemetry(raw_data)
            vibration = vibration_monitor.update(telemetry['vibration'])
            
            # Determine current flight phase
            flight_phase = determine_flight_phase(telemetry)
            
            # Run diagnostics
            anomaly_scores = detect_anomalies(telemetry, flight_phase=flight_phase)
            
            # Convert diagnostics to dictionary format
            engine_diag = convert_diagnostic(detect_engine_failure(telemetry))
            fuel_diag = convert_diagnostic(detect_fuel_emergency(telemetry))
            structural_diag = convert_diagnostic(detect_structural_failure(telemetry))
            
            # Analyze correlations
            correlations = analyze_system_correlations(engine_diag, fuel_diag, structural_diag).correlated_systems
            
            # Display information
            display_status(telemetry, vibration)
            display_anomalies(anomaly_scores)
            display_recommendations(vibration, correlations)
            
            print("\n" + "=" * 60)
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()
