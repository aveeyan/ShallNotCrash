# shallnotcrash/path_planner/runway_loader.py
"""
Loads and processes runway data from FlightGear's apt.dat file.
This provides high-quality, verified runway data to supplement OSM results.
"""
import os
import gzip
import shutil
import tempfile
import platform
import logging
import math
from typing import List, Optional, Tuple
from dataclasses import dataclass

# Using data models from the old runway.py for compatibility
@dataclass
class Runway:
    """Represents a single runway with its physical properties."""
    airport_code: str
    runway_id: str
    lat: float
    lon: float
    length_ft: int
    width_ft: int
    heading: float
    surface: str
    elevation_ft: float
    endpoint_1_lat: float
    endpoint_1_lon: float
    endpoint_2_lat: float
    endpoint_2_lon: float

class RunwayLoader:
    """Extracts runway data from FlightGear apt.dat files."""
    
    SURFACE_TYPES = {
        1: "Asphalt", 2: "Concrete", 3: "Turf", 4: "Dirt", 5: "Gravel",
        12: "Dry Lakebed", 13: "Water", 14: "Snow/Ice"
    }
    AIRPORT_CODES = {'1', '16', '17'} # airport, seaplane_base, heliport
    RUNWAY_CODES = {'100', '101'} # land runway, water runway
    
    def __init__(self):
        self.apt_dat_path = self._find_apt_dat()
        self.temp_dirs = []
        logging.info(f"RunwayLoader initialized. apt.dat path: {self.apt_dat_path}")

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
        """The core parsing logic, adapted from the original implementation."""
        runways = []
        current_airport = "N/A"
        current_elevation = 0.0
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                
                # Airport header line (e.g., "1 1302 1 KSQL San Carlos")
                if parts[0] in self.AIRPORT_CODES and len(parts) >= 5:
                    try:
                        current_elevation = float(parts[1])
                        current_airport = parts[4]
                    except (ValueError, IndexError):
                        continue # Ignore malformed airport lines
                
                # Runway line (e.g., "100 86.00 2 0 0 1 1 30 ...")
                elif parts[0] in self.RUNWAY_CODES and current_airport:
                    runway = self._parse_runway_line(parts, current_airport, current_elevation)
                    if runway:
                        dist_km = self._haversine_distance_km(center_lat, center_lon, runway.lat, runway.lon)
                        if dist_km <= radius_km:
                            runways.append(runway)
        return runways

    def _parse_runway_line(self, parts: List[str], airport_code: str, elevation_ft: float) -> Optional[Runway]:
        """Parses a single runway line from the apt.dat file."""
        try:
            if len(parts) < 19: return None # Not enough data for a runway

            # Extract runway properties
            width_ft = float(parts[1])
            surface_code = int(parts[2])
            
            # Endpoint 1 data
            runway_id1 = parts[8]
            lat1 = float(parts[9])
            lon1 = float(parts[10])
            
            # Endpoint 2 data
            runway_id2 = parts[17]
            lat2 = float(parts[18])
            lon2 = float(parts[19])

            # Basic validation
            if not (self._is_valid_coord(lat1, lon1) and self._is_valid_coord(lat2, lon2)):
                return None
            if abs(lat1 - lat2) < 1e-6 and abs(lon1 - lon2) < 1e-6:
                return None # Skip zero-length runways

            # Calculate properties
            center_lat = (lat1 + lat2) / 2
            center_lon = (lon1 + lon2) / 2
            length_m = self._haversine_distance_km(lat1, lon1, lat2, lon2) * 1000
            bearing = self._calculate_bearing(lat1, lon1, lat2, lon2)

            return Runway(
                airport_code=airport_code,
                runway_id=f"{runway_id1}/{runway_id2}",
                lat=center_lat,
                lon=center_lon,
                length_ft=int(length_m * 3.28084),
                width_ft=int(width_ft),
                heading=bearing,
                surface=self.SURFACE_TYPES.get(surface_code, "Unknown"),
                elevation_ft=elevation_ft,
                endpoint_1_lat=lat1,
                endpoint_1_lon=lon1,
                endpoint_2_lat=lat2,
                endpoint_2_lon=lon2,
            )
        except (ValueError, IndexError):
            return None # Malformed line

    def _haversine_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers."""
        R = 6371.0  # Earth radius in kilometers
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(math.radians, [lat1, lon1, lat2, lon2])
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points in degrees."""
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
        elif system == "Darwin": # macOS
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