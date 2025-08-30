import logging
from flask import Flask, render_template, jsonify
import threading
import time
import random
import subprocess
import os
import sys
import shutil
import socket
import signal
from shallnotcrash.landing_site.core import LandingSiteFinder
from shallnotcrash.path_planner.core import PathPlanner
from shallnotcrash.path_planner.data_models import AircraftState, Runway
from typing import List, Optional, Tuple

app = Flask(__name__)

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --- Globals and Locks ---
site_finder = LandingSiteFinder()
planner: Optional[PathPlanner] = None
current_position: Tuple[float, float] = (64.2306, -21.9406)
current_altitude: int = 5000
current_heading: int = 0
current_airspeed: int = 80
landing_site: Optional[Runway] = None
path: List = []
emergency_state: bool = False
search_radius_km: int = 50
fg_interface = None
flightgear_running: bool = False
flight_path_simulation = [
    (64.1306, -21.9406), (64.1500, -21.9000), (64.1700, -21.9500),
    (64.1400, -22.0000), (64.1100, -21.9800),
]
current_path_index: int = 0
state_lock = threading.Lock()

# --- Helper Functions ---
def check_flightgear_installation() -> Tuple[bool, Optional[str]]:
    """Check if FlightGear is properly installed and accessible."""
    fgfs_path = shutil.which('fgfs')
    if fgfs_path:
        logging.info(f"✓ FlightGear found at: {fgfs_path}")
        return True, fgfs_path
    else:
        logging.error("✗ FlightGear 'fgfs' command not found in PATH")
        return False, None

def check_port_availability(port: int = 5555) -> Tuple[bool, str]:
    """Check if the telnet port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(('localhost', port)) == 0:
                logging.info(f"✓ Port {port} is already in use (FlightGear might be running)")
                return False, "in_use"
            else:
                logging.info(f"✓ Port {port} is available")
                return True, "available"
    except Exception as e:
        logging.error(f"✗ Error checking port {port}: {e}")
        return False, "error"

def format_path_for_frontend(path_data) -> List[List[float]]:
    formatted_path = []
    if not path_data:
        return []
    for point in path_data:
        if hasattr(point, 'lat') and hasattr(point, 'lon'):
            formatted_path.append([point.lat, point.lon])
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            formatted_path.append([point[0], point[1]])
    return formatted_path

def initialize_path_planner(runways: List[Runway]) -> None:
    global planner
    if runways:
        planner = PathPlanner(available_runways=runways)
        logging.info(f"Path planner initialized with {len(runways)} runways.")
    else:
        planner = PathPlanner(available_runways=[])

def plan_emergency_route() -> None:
    global landing_site, path, planner
    try:
        raw_osm_data = site_finder.osm_loader.get_runways(current_position[0], current_position[1], search_radius_km)
        if not raw_osm_data:
            logging.warning("OSM loader returned no data. No landing sites found.")
            landing_site, path = None, []
            return
        available_runways = site_finder._parse_osm_data_to_runways(raw_osm_data)
        if not available_runways:
            logging.warning("Could not parse any runways from OSM data.")
            landing_site, path = None, []
            return
        landing_site = available_runways[0]
        logging.info(f"Selected landing site (runway): {landing_site.name}")
        initialize_path_planner([landing_site])
        if not planner:
            logging.error("Planner could not be initialized.")
            return
        aircraft_state = AircraftState(
            lat=current_position[0], lon=current_position[1],
            alt_ft=current_altitude, heading_deg=current_heading, airspeed_kts=current_airspeed
        )
        flight_path_obj = planner.generate_path(aircraft_state)
        if flight_path_obj and flight_path_obj.waypoints:
            path = flight_path_obj.waypoints
            logging.info(f"Path planned with {len(path)} waypoints.")
        else:
            logging.warning("Path planning failed. Creating fallback path.")
            path = [current_position, (landing_site.center_lat, landing_site.center_lon)]
    except Exception as e:
        logging.critical(f"Error during emergency planning: {e}", exc_info=True)
        if landing_site:
            path = [current_position, (landing_site.center_lat, landing_site.center_lon)]
        else:
            path = []

def launch_flightgear_async() -> dict:
    """
    Launches FlightGear in a detached process and logs its output for debugging.
    """
    try:
        fg_command = [
            "fgfs", "--airport=BIKF", "--aircraft=c172p", "--heading=280",
            "--altitude=2000", "--telnet=socket,bi,10,localhost,5555,tcp"
        ]
        log_path = os.path.join(os.path.dirname(__file__), 'flightgear_launch.log')
        logging.info(f"Attempting to launch FlightGear: {' '.join(fg_command)}")
        logging.info(f"FlightGear output will be logged to: {log_path}")

        with open(log_path, 'w') as log_file:
            subprocess.Popen(
                fg_command,
                stdout=log_file,
                stderr=log_file,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
        logging.info("FlightGear launch command issued successfully.")
        return {'success': True, 'message': 'Launch command sent.'}
    except FileNotFoundError:
        error_msg = "CRITICAL ERROR: FlightGear executable 'fgfs' not found in system PATH."
        logging.critical(error_msg)
        return {'success': False, 'message': error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred while launching FlightGear: {e}"
        logging.critical(error_msg, exc_info=True)
        return {'success': False, 'message': error_msg}

def connect_to_flightgear() -> bool:
    """Tries to connect to the FlightGear Telnet interface."""
    global fg_interface, flightgear_running
    try:
        from shallnotcrash.fg_interface.protocols.telnet import TelnetProtocol
        fg_interface = TelnetProtocol(host='localhost', port=5555, timeout=10.0)
        fg_interface.get("/position/latitude-deg")
        flightgear_running = True
        logging.info("Successfully connected to FlightGear.")
        return True
    except Exception as e:
        logging.warning(f"Failed to connect to FlightGear: {e}. Running in simulation mode.")
        flightgear_running = False
        return False

def update_telemetry() -> None:
    """
    Continuously updates telemetry data from either FlightGear or a simulation.
    This version has robust error handling for network issues.
    """
    global current_position, current_altitude, current_heading, current_airspeed, emergency_state, current_path_index, flightgear_running
    while True:
        try:
            with state_lock:
                if flightgear_running and fg_interface:
                    try:
                        lat = fg_interface.get("/position/latitude-deg")
                        lon = fg_interface.get("/position/longitude-deg")
                        alt = fg_interface.get("/position/altitude-ft")
                        hdg = fg_interface.get("/orientation/heading-deg")
                        spd = fg_interface.get("/velocities/airspeed-kt")
                        current_position = (lat, lon)
                        current_altitude = alt
                        current_heading = hdg
                        current_airspeed = spd
                    except (socket.timeout) as e:
                        logging.warning(f"Telemetry update failed with a transient error: {e}. Retrying.")
                    except (ConnectionRefusedError, BrokenPipeError) as e:
                        logging.error(f"FlightGear connection lost: {e}. Reverting to simulation mode.")
                        flightgear_running = False
                else:
                    current_path_index = (current_path_index + 1) % len(flight_path_simulation)
                    current_position = flight_path_simulation[current_path_index]
                    current_altitude += random.randint(-20, 20)
                    current_heading = (current_heading + 5) % 360
                    current_airspeed += random.randint(-2, 2)
                if emergency_state:
                    plan_emergency_route()
        except Exception as e:
            logging.critical(f"A critical unexpected error occurred in the telemetry loop: {e}", exc_info=True)
            flightgear_running = False
        time.sleep(1.0)

# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('map.html')

@app.route('/start_fg', methods=['POST'])
def start_fg():
    """
    Checks prerequisites and then launches FlightGear in a background thread.
    """
    fg_installed, _ = check_flightgear_installation()
    if not fg_installed:
        return jsonify({'success': False, 'message': "'fgfs' not found. Please install FlightGear and ensure it's in your PATH."}), 400
    port_available, status = check_port_availability(5555)
    if not port_available and status == "in_use":
        logging.info("Port 5555 is busy. Attempting to connect to existing FlightGear instance.")
        connect_to_flightgear()
        return jsonify({'success': True, 'message': 'FlightGear appears to be running already. Connection attempted.'})
    def launch_and_connect():
        result = launch_flightgear_async()
        if result['success']:
            logging.info("Waiting for FlightGear to start up...")
            time.sleep(15)
            logging.info("Attempting to auto-connect after launch...")
            connect_to_flightgear()
    launch_thread = threading.Thread(target=launch_and_connect, daemon=True)
    launch_thread.start()
    return jsonify({'success': True, 'message': 'FlightGear launch initiated. It may take a moment to start.'})

@app.route('/position')
def get_position():
    with state_lock:
        return jsonify({
            'lat': current_position[0],
            'lng': current_position[1],
            'alt': current_altitude,
            'heading': current_heading,
            'airspeed': current_airspeed,
            'emergency': emergency_state,
            'flightgear_connected': flightgear_running
        })

@app.route('/landing_site')
def get_landing_site():
    with state_lock:
        if landing_site:
            return jsonify({'lat': landing_site.center_lat, 'lng': landing_site.center_lon, 'name': landing_site.name})
        return jsonify({})

@app.route('/path')
def get_path():
    with state_lock:
        return jsonify(format_path_for_frontend(path))

@app.route('/emergency/<state>')
def set_emergency(state):
    global emergency_state, path, landing_site
    with state_lock:
        is_emergency = state.lower() == 'true'
        if is_emergency and not emergency_state:
            logging.info("Manual emergency trigger activated.")
            emergency_state = True
            plan_emergency_route()
        elif not is_emergency and emergency_state:
            logging.info("Emergency state reset.")
            emergency_state = False
            path, landing_site = [], None
        return jsonify({'emergency': emergency_state})

@app.route('/connect_fg')
def connect_fg():
    success = connect_to_flightgear()
    return jsonify({'connected': success})

def shutdown_handler(signum, frame):
    logging.info("Received shutdown signal. Exiting gracefully.")
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    logging.info("=" * 60)
    logging.info("Emergency Landing System - BIKF Area")
    logging.info("=" * 60)
    thread = threading.Thread(target=update_telemetry, daemon=True)
    thread.start()
    app.run(debug=True, use_reloader=False, threaded=True)
