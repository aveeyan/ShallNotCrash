#!/usr/bin/env python3
# shallnotcrash/examples/E040_engine_failure_detection.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.emergency.protocols import detect_engine_failure
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

    print("Monitoring engine health. Press Ctrl+C to stop...")

    try:
        while True:
            # Get engine telemetry values with safe access
            telemetry = {
                'rpm': safe_get(fg, FGProps.ENGINE.RPM),
                'cht': safe_get(fg, FGProps.ENGINE.CHT_F),
                'oil_press': safe_get(fg, FGProps.ENGINE.OIL_PRESS_PSI),
                'oil_temp': safe_get(fg, FGProps.ENGINE.OIL_TEMP_F),
                'fuel_flow': safe_get(fg, FGProps.ENGINE.FUEL_FLOW_GPH),
                'egt': safe_get(fg, FGProps.ENGINE.EGT_F),
            }
            print(telemetry)
            
            # Get diagnostic status
            diagnostic = detect_engine_failure(telemetry)
            
            print("\n=== ENGINE DIAGNOSTICS ===")
            print(f"Status: {'FAILURE' if diagnostic.is_failure else 'NORMAL'}")
            print(f"Severity: {diagnostic.severity.name}")
            print(f"Confidence: {diagnostic.confidence:.0%}")
            
            # # Display diagnostics for each parameter
            # for param, data in diagnostic.diagnostics.items():
            #     print(f"\n{param.upper()}:")
            #     print(f"  Value: {data['value']}")
            #     print(f"  Status: {data['status']}")
            #     print(f"  Message: {data['message']}")
            
            # if diagnostic.is_failure:
            #     print("\n!!! ENGINE FAILURE DETECTED !!!")
            #     print("Affected components:", ", ".join(diagnostic.failed_components))
            #     print("Recommended actions:")
            #     print("- Reduce power immediately")
            #     print("- Monitor parameters closely")
            #     print("- Prepare for emergency landing")
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()