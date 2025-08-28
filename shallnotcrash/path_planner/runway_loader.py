# shallnotcrash/path_planner/runway_loader.py
"""
[REFACTORED - V4 - DEFINITIVE]
Loads and processes runway data from FlightGear's apt.dat file.

CRITICAL CHANGE: The class is renamed to 'AptDatLoader' to permanently
resolve the name collision with the OSM loader in the 'landing_site' package.
This class now correctly uses the canonical 'Runway' data model from this package.
"""
import os
import gzip
import shutil
import tempfile
import platform
import logging
import math
from typing import List, Optional

# --- Use the canonical Runway data model from this package ---
from .data_models import Runway

# --- [THE DEFINITIVE FIX] Class renamed to be unique and descriptive. ---
class AptDatLoader:
    """Extracts runway data from FlightGear apt.dat files."""
    
    SURFACE_TYPES = {
        1: "Asphalt", 2: "Concrete", 3: "Turf", 4: "Dirt", 5: "Gravel",
        12: "Dry Lakebed", 13: "Water", 14: "Snow/Ice"
    }
    AIRPORT_CODES = {'1', '16', '17'}
    RUNWAY_CODES = {'100', '101'}
    
    def __init__(self):
        self.apt_dat_path = self._find_apt_dat()
        self.temp_dirs = []
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(f"AptDatLoader initialized. Path: {self.apt_dat_path}")

    def load_runways_in_radius(self, center_lat: float, center_lon: float, radius_km: float) -> List[Runway]:
        """Extracts all runways within a given radius of a center point."""
        if not self.apt_dat_path:
            logging.warning("apt.dat file not found. Cannot load runway data.")
            return []
        
        try:
            extracted_path = self._extract_gzip_file(self.apt_dat_path)
            runways = self._parse_runways(extracted_path, center_lat, center_lon, radius_km)
            logging.info(f"Found {len(runways)} runways in apt.dat within {radius_km}km radius.")
            return runways
        except Exception as e:
            logging.error(f"Failed to load or parse runway data: {e}")
            return []
        finally:
            self._cleanup()

    def _parse_runways(self, file_path: str, center_lat: float, center_lon: float, radius_km: float) -> List[Runway]:
        runways = []
        current_airport = "N/A"
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split()
                if not parts: continue
                
                if parts[0] in self.AIRPORT_CODES and len(parts) >= 5:
                    current_airport = parts[4]
                
                elif parts[0] in self.RUNWAY_CODES and current_airport:
                    runway = self._parse_runway_line(parts, current_airport)
                    if runway:
                        dist_km = self._haversine_distance_km(center_lat, center_lon, runway.center_lat, runway.center_lon)
                        if dist_km <= radius_km:
                            runways.append(runway)
        return runways

    def _parse_runway_line(self, parts: List[str], airport_code: str) -> Optional[Runway]:
        try:
            if len(parts) < 20: return None

            width_ft = float(parts[1])
            surface_code = int(parts[2])
            runway_id1 = parts[8]
            lat1 = float(parts[9])
            lon1 = float(parts[10])
            runway_id2 = parts[17]
            lat2 = float(parts[18])
            lon2 = float(parts[19])

            if not (self._is_valid_coord(lat1, lon1) and self._is_valid_coord(lat2, lon2)): return None
            if abs(lat1 - lat2) < 1e-6 and abs(lon1 - lon2) < 1e-6: return None

            center_lat = (lat1 + lat2) / 2
            center_lon = (lon1 + lon2) / 2
            length_m = self._haversine_distance_km(lat1, lon1, lat2, lon2) * 1000
            width_m = width_ft * 0.3048
            bearing = self._calculate_bearing(lat1, lon1, lat2, lon2)
            surface = self.SURFACE_TYPES.get(surface_code, "Unknown")
            name = f"{airport_code} {runway_id1}/{runway_id2}"

            return Runway(
                name=name, start_lat=lat1, start_lon=lon1, end_lat=lat2, end_lon=lon2,
                center_lat=center_lat, center_lon=center_lon, bearing_deg=bearing,
                length_m=length_m, width_m=width_m, surface_type=surface
            )
        except (ValueError, IndexError):
            return None

    def _haversine_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2_rad - lon1_rad
        y = math.sin(dlon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def _is_valid_coord(self, lat: float, lon: float) -> bool:
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
    
    def _find_apt_dat(self) -> Optional[str]:
        system = platform.system()
        paths = []
        if system == "Linux":
            paths = ["/usr/share/games/flightgear/Airports/apt.dat.gz", "/usr/share/flightgear/Airports/apt.dat.gz", os.path.expanduser("~/.fgfs/Airports/apt.dat.gz")]
        elif system == "Windows":
            paths = [os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "FlightGear", "data", "Airports", "apt.dat.gz")]
        elif system == "Darwin":
            paths = ["/Applications/FlightGear.app/Contents/Resources/data/Airports/apt.dat.gz"]
        
        for path in paths:
            if os.path.exists(path):
                return path
        return None

    def _extract_gzip_file(self, gz_path: str) -> str:
        temp_dir = tempfile.mkdtemp(prefix="shallnotcrash_")
        self.temp_dirs.append(temp_dir)
        extracted_path = os.path.join(temp_dir, "apt.dat")
        with gzip.open(gz_path, 'rb') as f_in:
            with open(extracted_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        return extracted_path

    def _cleanup(self):
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.temp_dirs.clear()

    def __del__(self):
        self._cleanup()