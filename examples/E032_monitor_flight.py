#!/usr/bin/env python3
# shallnotcrash/examples/E032_monitor_flight.py

import time
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.airplane.systems.flight import FlightSystem
from shallnotcrash.airplane.constants import C172PConstants

def main():
    print("Connecting to FlightGear...")
    fg = FGConnection()
    conn_result = fg.connect()
    
    if not conn_result['success']:
        print(f"Connection failed: {conn_result['message']}")
        return

    flight_monitor = FlightSystem(fg)
    print("Monitoring flight parameters. Press Ctrl+C to stop...")

    try:
        while True:
            flight_status = flight_monitor.update()
            print(flight_status)
            if 'error' in flight_status:
                print(f"Error: {flight_status['error']}")
            else:
                print("\n=== FLIGHT STATUS ===")
                # Access nested dicts properly
                position = flight_status['position']
                attitude = flight_status['attitude']
                speed = flight_status['speed']

                print(f"Altitude: {position['altitude_ft']:.1f} ft")
                print(f"Altitude AGL: {position['agl_ft']:.1f} ft")
                print(f"Ground Elevation: {position['ground_elev_ft']:.1f} ft")
                print(f"Latitude: {position['latitude_deg']:.6f}")
                print(f"Longitude: {position['longitude_deg']:.6f}")
                
                print(f"Roll: {attitude['roll_deg']:.1f}°")
                print(f"Pitch: {attitude['pitch_deg']:.1f}°")
                print(f"Heading: {attitude['heading_deg']:.1f}°")
                
                print(f"Airspeed: {speed['airspeed_kt']:.1f} kt")
                print(f"Vertical Speed: {speed['vertical_speed_fps']:.1f} ft/s")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")

if __name__ == "__main__":
    main()
