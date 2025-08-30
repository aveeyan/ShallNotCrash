import logging
import threading
import time
import subprocess
import queue
from flask import Flask, render_template, jsonify, request
from shallnotcrash.fg_interface.protocols.telnet import TelnetProtocol
from shallnotcrash.constants.connection import FGConnectionConstants
from shallnotcrash.constants.flightgear import FGProps

app = Flask(__name__)

fg_interface = None
fg_connected = False
telemetry_queue = queue.Queue(maxsize=1)
last_good = {
    'lat': None,
    'lng': None,
    'heading': None,
    'speed': None,
    'altitude': None,  # Add this line
    'fg_connected': False
}

def try_connect_fg():
    global fg_interface, fg_connected
    try:
        fg_interface = TelnetProtocol(
            host=FGConnectionConstants.DEFAULT_HOST,
            port=FGConnectionConstants.DEFAULT_PORT,
            timeout=2.0
        )
        fg_interface.get(FGProps.FLIGHT.LATITUDE)
        fg_connected = True
        logging.info("Connected to FlightGear via Telnet.")
    except Exception as e:
        fg_interface = None
        fg_connected = False
        logging.warning(f"Could not connect to FlightGear: {e}")

def telemetry_worker():
    global fg_connected, last_good
    failure_count = 0
    max_failures = 5
    while True:
        data = last_good.copy()
        if fg_connected and fg_interface:
            try:
                data['lat'] = fg_interface.get(FGProps.FLIGHT.LATITUDE)
                data['lng'] = fg_interface.get(FGProps.FLIGHT.LONGITUDE)
                data['heading'] = fg_interface.get(FGProps.FLIGHT.HEADING_DEG)
                data['speed'] = fg_interface.get(FGProps.FLIGHT.AIRSPEED_KT)
                data['altitude'] = fg_interface.get(FGProps.FLIGHT.ALTITUDE_FT)  # Add this line
                data['fg_connected'] = True
                failure_count = 0
                last_good = data.copy()
            except Exception as e:
                failure_count += 1
                logging.warning(f"FG read failed ({failure_count}/{max_failures}): {e}")
                if failure_count >= max_failures:
                    fg_connected = False
                    data = last_good.copy()
                    data['fg_connected'] = False
        else:
            data = last_good.copy()
            data['fg_connected'] = False
        try:
            telemetry_queue.get_nowait()
        except queue.Empty:
            pass
        telemetry_queue.put(data)
        time.sleep(0.1)
        
@app.route('/')
def index():
    return render_template('hud.html')

@app.route('/position')
def position():
    global last_good
    try:
        data = telemetry_queue.get_nowait()
        # Only update last_good if fg_connected is True
        if data.get('fg_connected'):
            last_good = data.copy()
    except queue.Empty:
        data = last_good.copy()
    return jsonify(data)

@app.route('/start_fg', methods=['POST'])
def start_fg():
    fg_command = [
        "fgfs",
        "--airport=BIKF",
        "--aircraft=c172p",
        "--heading=280",
        "--altitude=2000",
        f"--telnet=socket,bi,10,{FGConnectionConstants.DEFAULT_HOST},{FGConnectionConstants.DEFAULT_PORT},tcp"
    ]
    try:
        subprocess.Popen(fg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(12)
        try_connect_fg()
        return jsonify({'success': fg_connected})
    except Exception as e:
        logging.error(f"Failed to start FlightGear: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/connect_fg')
def connect_fg():
    try_connect_fg()
    return jsonify({'fg_connected': fg_connected})

if __name__ == '__main__':
    try_connect_fg()
    threading.Thread(target=telemetry_worker, daemon=True).start()
    app.run(debug=True)
