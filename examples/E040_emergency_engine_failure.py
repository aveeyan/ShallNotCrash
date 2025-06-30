#!/usr/bin/env python3
# shallnotcrash/examples/E040_emergency_engine_failure.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.airplane.systems.engine import EngineSystem
from shallnotcrash.emergency.protocols.engine_failure import ENGINE_FAILURE_PROTOCOL
from shallnotcrash.constants.flightgear import FGProps

def main():
    print("Connecting to FlightGear...")
    fg = FGConnection()
    conn_result = fg.connect()
    
    if not conn_result['success']:
        print(f"Connection failed: {conn_result['message']}")
        return

    engine_monitor = EngineSystem(fg)
    print("Monitoring engine parameters. Press Ctrl+C to stop...")

    try:
        while True:
            # Get individual telemetry values
            telemetry = {
                FGProps.ENGINE.RPM: fg.get(FGProps.ENGINE.RPM)['data']['value'],
                FGProps.ENGINE.CHT_F: fg.get(FGProps.ENGINE.CHT_F)['data']['value'],
                FGProps.ENGINE.OIL_PRESS_PSI: fg.get(FGProps.ENGINE.OIL_PRESS_PSI)['data']['value'],
                FGProps.ENGINE.OIL_TEMP_F: fg.get(FGProps.ENGINE.OIL_TEMP_F)['data']['value'],
                FGProps.ENGINE.FUEL_FLOW_GPH: fg.get(FGProps.ENGINE.FUEL_FLOW_GPH)['data']['value'],
                FGProps.ENGINE.EGT_F: fg.get(FGProps.ENGINE.EGT_F)['data']['value']
            }
            
            # Get engine status from system
            engine_status = engine_monitor.update()
            
            print("\n=== ENGINE STATUS ===")
            # Display key parameters
            print(f"RPM: {engine_status['rpm']:.0f}")
            print(f"CHT: {engine_status['cht']:.0f}°F")
            print(f"Oil Temp: {engine_status['oil_temp']:.0f}°F")
            print(f"Oil Pressure: {engine_status['oil_pressure']:.1f} psi")
            print(f"Fuel Flow: {engine_status['fuel_flow']:.1f} GPH")
            print(f"EGT: {engine_status['egt']:.0f}°F")
            
            # Check for potential engine failure
            checklist = ENGINE_FAILURE_PROTOCOL.get_actions(telemetry)
            if checklist:
                print("\n!!! POSSIBLE ENGINE FAILURE PROTOCOL !!!")
                for action in checklist:
                    print(f"- {action}")
            
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()
