# /examples/E010_communicator.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from shallnotcrash.fg_interface import FGConnection
from shallnotcrash.constants.flightgear import FGProps

# Connect
fg = FGConnection()
result = fg.connect()
if not result["success"]:
    print(f"Failed: {result['message']}")
    exit(1)

# Read data
latitude = fg.get(FGProps.FLIGHT.LATITUDE)
print(f"Latitude Raw:\n{latitude}")
longitude = fg.get(FGProps.FLIGHT.LONGITUDE)
print(f"Longitude Raw:\n{longitude}")

if latitude["success"]:
    print(f"Current latitude: {latitude['data']['value']}")
    print(f"Current longitude: {longitude['data']['value']}")