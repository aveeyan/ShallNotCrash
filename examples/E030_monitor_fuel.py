#!/usr/bin/env python3
# shallnotcrash/examples/E030_monitor_fuel.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.airplane.systems.fuel import FuelSystem
from shallnotcrash.airplane.constants import C172PConstants

def main():
    print("Connecting to FlightGear...")
    fg = FGConnection()
    conn_result = fg.connect()
    
    if not conn_result['success']:
        print(f"Connection failed: {conn_result['message']}")
        return

    fuel_monitor = FuelSystem(fg)
    print("Monitoring fuel levels. Press Ctrl+C to stop...")
    print(f"Fuel density: {C172PConstants.FUEL['DENSITY_PPG']} lbs/gal")

    try:
        while True:
            fuel_status = fuel_monitor.update()
            
            if 'error' in fuel_status:
                print(f"Error: {fuel_status['error']}")
            else:
                print("\n=== FUEL STATUS ===")
                print(f"Left Tank: {fuel_status['tanks']['left']['gallons']:.4f} gal")
                print(f"Right Tank: {fuel_status['tanks']['right']['gallons']:.4f} gal")
                print(f"Total: {fuel_status['total_gal']:.1f} gal (Usable: {C172PConstants.FUEL['USABLE_CAPACITY_GAL']} gal)")
                print(f"Status: {fuel_status['status']}")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()