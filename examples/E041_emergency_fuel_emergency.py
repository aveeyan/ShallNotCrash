#!/usr/bin/env python3
# shallnotcrash/examples/E041_emergency_fuel_emergency.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.emergency.protocols import detect_fuel_emergency
from shallnotcrash.airplane.constants import C172PConstants
from shallnotcrash.constants.flightgear import FGProps

def safe_get(fg_conn, property_path, default=0.0):
    """Safely get property value with error handling"""
    try:
        response = fg_conn.get(property_path)
        if response['success'] and 'data' in response and 'value' in response['data']:
            return response['data']['value']
        return default
    except (KeyError, TypeError):
        return default

def main():
    print("Connecting to FlightGear...")
    fg = FGConnection()
    conn_result = fg.connect()
    
    if not conn_result['success']:
        print(f"Connection failed: {conn_result['message']}")
        return

    print("Monitoring fuel system. Press Ctrl+C to stop...")
    print(f"Useable fuel capacity: {C172PConstants.FUEL['USABLE_CAPACITY_GAL']} gal")
    print(f"Critical threshold: {C172PConstants.FUEL['CRITICAL_THRESHOLD_GAL']} gal")

    try:
        while True:
            # Get fuel system telemetry
            telemetry = {
                'fuel_left': safe_get(fg, FGProps.FUEL.LEFT_QTY_GAL),
                'fuel_right': safe_get(fg, FGProps.FUEL.RIGHT_QTY_GAL),
                'fuel_flow': safe_get(fg, FGProps.ENGINE.FUEL_FLOW_GPH),
                'selector': safe_get(fg, FGProps.FUEL.SELECTOR),
                'pump': safe_get(fg, FGProps.FUEL.PUMP)
            }
            
            # Calculate total fuel
            telemetry['total_fuel'] = telemetry['fuel_left'] + telemetry['fuel_right']
            
            # Get diagnostic status
            diagnostic = detect_fuel_emergency(telemetry)
            
            # Print telemetry
            print("\n=== FUEL SYSTEM STATUS ===")
            print(f"Left Tank: {telemetry['fuel_left']:.1f} gal")
            print(f"Right Tank: {telemetry['fuel_right']:.1f} gal")
            print(f"Total Fuel: {telemetry['total_fuel']:.1f} gal")
            print(f"Fuel Flow: {telemetry['fuel_flow']:.1f} GPH")
            print(f"Selector: {_selector_position(telemetry['selector'])}")
            print(f"Pump: {'ON' if telemetry['pump'] else 'OFF'}")
            
            # Print diagnostics
            print("\n=== FUEL EMERGENCY DIAGNOSTICS ===")
            print(f"Status: {'EMERGENCY' if diagnostic.is_emergency else 'NORMAL'}")
            print(f"Severity: {diagnostic.severity.name}")
            print(f"Confidence: {diagnostic.confidence:.0%}")
            
            print("\nDetailed Diagnostics:")
            for param, data in diagnostic.diagnostics.items():
                print(f"\n{param.upper()}:")
                print(f"  Value: {data['value']}")
                print(f"  Status: {data['status']}")
                print(f"  Message: {data['message']}")
                print(f"  Normal Range: {data['normal_range']}")
                print(f"  Critical Threshold: {data['critical_threshold']}")
            
            if diagnostic.is_emergency:
                print("\n!!! FUEL EMERGENCY DETECTED !!!")
                print("Affected components:", ", ".join(diagnostic.failed_components))
                print("Recommended actions:")
                print("- Switch fuel selector to fullest tank")
                print("- Turn on fuel pump immediately")
                print("- Prepare for emergency landing")
            
            time.sleep(2)

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