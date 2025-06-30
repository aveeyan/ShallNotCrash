#!/usr/bin/env python3
# shallnotcrash/examples/E040_emergency_fuel_emergency.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.airplane.systems.fuel import FuelSystem
from shallnotcrash.emergency.protocols.fuel_emergency import FUEL_EMERGENCY_PROTOCOL
from shallnotcrash.airplane.constants import C172PConstants

def main():
    print("Connecting to FlightGear...")
    fg = FGConnection()
    conn_result = fg.connect()
    
    if not conn_result['success']:
        print(f"Connection failed: {conn_result['message']}")
        return

    fuel_monitor = FuelSystem(fg)
    print("Monitoring fuel system parameters. Press Ctrl+C to stop...")
    print(f"Fuel density: {C172PConstants.FUEL['DENSITY_PPG']} lbs/gal")

    try:
        while True:
            # Get processed fuel system status
            fuel_status = fuel_monitor.update()
            
            # Check for errors first
            if 'error' in fuel_status:
                print(f"Error: {fuel_status['error']}")
                time.sleep(2)
                continue
                
            # Build telemetry in the format expected by the protocol
            telemetry = {
                'fuel_left': fuel_status['tanks']['left']['gallons'],
                'fuel_right': fuel_status['tanks']['right']['gallons'],
                'total_fuel': fuel_status['total_gal'],
                'fuel_flow': fuel_status.get('fuel_flow', 0.0),
                'selector': fuel_status.get('selector', 3),
                'pump': fuel_status.get('pump', 0)
            }
            
            print("\n=== FUEL SYSTEM STATUS ===")
            # Display key parameters (match E030 format)
            print(f"Left Tank: {telemetry['fuel_left']:.4f} gal")
            print(f"Right Tank: {telemetry['fuel_right']:.4f} gal")
            print(f"Total: {telemetry['total_fuel']:.1f} gal (Usable: {C172PConstants.FUEL['USABLE_CAPACITY_GAL']} gal)")
            print(f"Fuel Flow: {telemetry['fuel_flow']:.1f} GPH")
            print(f"Status: {fuel_status.get('status', 'NORMAL')}")
            print(f"Endurance: {fuel_status.get('endurance_min', 0):.0f} min")
            print(f"Fuel Selector: {_selector_position(telemetry['selector'])}")
            
            # Check for potential fuel emergency
            checklist = FUEL_EMERGENCY_PROTOCOL.get_actions(telemetry)
            if checklist:
                print("\n!!! FUEL EMERGENCY PROTOCOL !!!")
                for action in checklist:
                    print(f"- {action}")
            
            time.sleep(2)  # Match update frequency of E030

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

def _selector_position(value: float) -> str:
    """Convert numeric selector value to human-readable position"""
    positions = {
        0: "OFF",
        1: "LEFT",
        2: "RIGHT",
        3: "BOTH"
    }
    return positions.get(int(value), "UNKNOWN")

if __name__ == "__main__":
    main()
