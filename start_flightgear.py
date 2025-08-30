#!/usr/bin/env python3
"""
FlightGear Launcher for BIKF Emergency Landing System
This script starts FlightGear with Cessna 172P at BIKF airport
"""

import subprocess
import os
import sys
import time

def check_flightgear_installed():
    """Check if FlightGear is available in PATH"""
    try:
        subprocess.run(["fgfs", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def start_flightgear():
    """Start FlightGear with the correct parameters"""
    
    if not check_flightgear_installed():
        print("FlightGear is not installed or not in PATH")
        print("Please install FlightGear first:")
        print("Ubuntu/Debian: sudo apt install flightgear")
        print("Or download from: https://www.flightgear.org/")
        return False
    
    # FlightGear command parameters
    fg_command = [
        "fgfs",
        "--aircraft=c172p",
        "--lat=64.1306",
        "--lon=-21.9406", 
        "--heading=0",
        "--altitude=2000",
        "--vc=80",
        "--telnet=socket,bi,0.5,localhost,5555,tcp",
        "--httpd=5500",
        "--timeofday=noon",
        "--disable-real-weather-fetch",
        "--enable-hud",
        "--enable-panel",
        "--prop:/sim/rendering/random-vegetation=false",
        "--prop:/sim/rendering/random-buildings=false",
        "--prop:/sim/rendering/clouds3d-enable=false"
    ]
    
    print("Starting FlightGear with Cessna 172P at BIKF Airport...")
    print("Aircraft will be positioned at: Latitude 64.1306, Longitude -21.9406")
    print("Web interface will be available at: http://localhost:5000")
    print("FlightGear web interface at: http://localhost:5500")
    print("Telnet interface at: localhost:5555")
    print("\nPress Ctrl+C to stop FlightGear")
    
    try:
        # Start FlightGear
        process = subprocess.Popen(fg_command)
        
        # Wait for FlightGear to start (or until interrupted)
        print("FlightGear started successfully!")
        print("You can now run the Flask app in another terminal: python3 app.py")
        print("Then open: http://localhost:5000")
        
        process.wait()
        return True
        
    except KeyboardInterrupt:
        print("\nStopping FlightGear...")
        if process:
            process.terminate()
        return True
    except Exception as e:
        print(f"Error starting FlightGear: {e}")
        return False

if __name__ == "__main__":
    start_flightgear()