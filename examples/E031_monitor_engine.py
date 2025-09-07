#!/usr/bin/env python3
# shallnotcrash/examples/E031_monitor_engine.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.airplane.systems.engine import EngineSystem
from shallnotcrash.airplane.constants import C172PConstants

def main():
    print("Connecting to FlightGear...")
    fg = FGConnection()
    conn_result = fg.connect()
    
    if not conn_result['success']:
        print(f"Connection failed: {conn_result['message']}")
        return

    engine_monitor = EngineSystem(fg)
    print("Monitoring engine parameters. Press Ctrl+C to stop...")
    print(f"Redline RPM: {C172PConstants.ENGINE['REDLINE_RPM']}")
    print(f"Max EGT: {C172PConstants.ENGINE['MAX_EGT']}°F")

    try:
        while True:
            engine_status = engine_monitor.update()
            
            if 'error' in engine_status:
                print(f"Error: {engine_status['error']}")
            else:
                print("\n=== ENGINE STATUS ===")
                print(f"RPM: {engine_status['rpm']:.0f} (Redline: {C172PConstants.ENGINE['REDLINE_RPM']})")
                print(f"EGT: {engine_status['egt']:.0f}°F (Max: {C172PConstants.ENGINE['MAX_EGT']}°F)")
                print(f"CHT: {engine_status['cht']:.0f}°F")
                print(f"Oil: {engine_status['oil_temp']:.0f}°F / {engine_status['oil_pressure']:.1f} psi")
                print(f"Fuel Flow: {engine_status['fuel_flow']:.1f} GPH")
                print(f"Status: {engine_status['status']}")
                
                # Display maintenance info if available
                if 'maintenance' in engine_status:
                    print(f"\nMaintenance:")
                    print(f"  Hours since oil change: {engine_status['maintenance']['hours_since_oil_change']:.1f}")
                    print(f"  Next oil change in: {engine_status['maintenance']['next_oil_change_due']:.1f} hours")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()