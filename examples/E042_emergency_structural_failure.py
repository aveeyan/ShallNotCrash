#!/usr/bin/env python3
# shallnotcrash/examples/E042_structural_failure_detection.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.emergency.protocols.structural_failure import detect_structural_failure  # Corrected import
from shallnotcrash.constants.flightgear import FGProps

def safe_get(fg_conn, property_path, default=0.0):
    """Safely get property value with error handling"""
    try:
        response = fg_conn.get(property_path)
        if response['success'] and 'data' in response and 'value' in response['data']:
            return response['data']['value']
        return default
    except KeyError:
        return default

def main():
    print("Connecting to FlightGear...")
    fg = FGConnection()
    conn_result = fg.connect()
    
    if not conn_result['success']:
        print(f"Connection failed: {conn_result['message']}")
        return

    print("Monitoring structural integrity. Press Ctrl+C to stop...")

    try:
        while True:
            # Get structural telemetry values with safe access
            telemetry = {
                'control_asymmetry': (abs(safe_get(fg, FGProps.CONTROLS.AILERON)) +
                                     abs(safe_get(fg, FGProps.CONTROLS.ELEVATOR)) +
                                     abs(safe_get(fg, FGProps.CONTROLS.RUDDER))),
                'g_load': abs(safe_get(fg, FGProps.FLIGHT.ACCEL_Z)) / 32.2  # Convert to Gs
            }
            print(telemetry)
            
            # Get diagnostic status
            diagnostic = detect_structural_failure(telemetry)
            
            print("\n=== STRUCTURAL INTEGRITY DIAGNOSTICS ===")
            print(f"Status: {'FAILURE' if diagnostic.is_failure else 'NORMAL'}")
            print(f"Severity: {diagnostic.severity.name}")
            print(f"Confidence: {diagnostic.confidence:.0%}")
            
            print("\nDetailed Diagnostics:")
            for param, data in diagnostic.diagnostics.items():
                print(f"\n{param.upper()}:")
                print(f"  Value: {data['value']}")
                print(f"  Status: {data['status']}")
                print(f"  Message: {data['message']}")
                print(f"  Warning Threshold: {data['warning_threshold']}")
                print(f"  Critical Threshold: {data['critical_threshold']}")
            
            if diagnostic.is_failure:
                print("\n!!! STRUCTURAL FAILURE DETECTED !!!")
                print("Affected components:", ", ".join(diagnostic.failed_components))
                print("Recommended actions:")
                print("- Reduce airspeed immediately")
                print("- Avoid aggressive maneuvers")
                print("- Prepare for emergency landing")
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()