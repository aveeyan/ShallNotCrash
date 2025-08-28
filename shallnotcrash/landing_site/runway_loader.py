# shallnotcrash/landing_site/runway_loader.py
"""
[CORRECT IMPLEMENTATION - V2]
This module provides the network-based RunwayLoader responsible for fetching
runway data from the OpenStreetMap (OSM) Overpass API.

This is the correct class for this file location, providing the `get_runways`
method that other parts of the system expect.
"""
import requests
import logging
import os
import json
import time
from typing import List, Dict, Any, Optional

class RunwayLoader:
    """
    Fetches runway data from the OSM Overpass API. It includes caching to
    avoid repeated network requests for the same area.
    """
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".shallnotcrash_cache")
    CACHE_EXPIRY_SECONDS = 86400  # 24 hours

    def __init__(self, timeout: int = 180):
        self.timeout = timeout
        if not os.path.exists(self.CACHE_DIR):
            os.makedirs(self.CACHE_DIR, exist_ok=True)
        
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info("Network RunwayLoader (OSM) initialized.")

    def get_runways(self, lat: float, lon: float, radius_km: int) -> Optional[List[Dict[str, Any]]]:
        """
        [THE REQUIRED METHOD]
        Queries the Overpass API for runways within a specified radius of a
        latitude/longitude point. Returns the raw 'elements' list from the API.
        """
        cache_path = self._get_cache_path(lat, lon, radius_km)
        
        # Try loading from cache first
        cached_data = self._load_from_cache(cache_path)
        if cached_data is not None:
            logging.info(f"Loaded runway data from cache: {cache_path}")
            return cached_data

        # If not in cache, query the network
        logging.info(f"No valid cache found. Querying Overpass API for runways at ({lat}, {lon})...")
        radius_m = radius_km * 1000
        query = self._build_overpass_query(lat, lon, radius_m)
        
        try:
            response = requests.post(self.OVERPASS_URL, data=query, timeout=self.timeout)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            
            data = response.json()
            elements = data.get('elements', [])
            self._save_to_cache(cache_path, data) # Cache the full response
            
            return elements
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error querying Overpass API: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON response from Overpass API: {e}")
            return None

    def _build_overpass_query(self, lat: float, lon: float, radius_m: int) -> str:
        """Constructs the Overpass QL query string."""
        return f"""
        [out:json][timeout:{self.timeout}];
        (
          way["aeroway"="runway"](around:{radius_m},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """

    def _get_cache_path(self, lat: float, lon: float, radius_km: int) -> str:
        """Creates a standardized filename for a given query."""
        filename = f"osm_{lat:.4f}_{lon:.4f}_{radius_km}km.json"
        return os.path.join(self.CACHE_DIR, filename)

    def _load_from_cache(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """Loads data from a cache file if it exists and is not expired."""
        if os.path.exists(file_path):
            file_mod_time = os.path.getmtime(file_path)
            if (time.time() - file_mod_time) < self.CACHE_EXPIRY_SECONDS:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        return data.get('elements') # Return elements or None if key missing
                except (json.JSONDecodeError, IOError):
                    return None
        return None

    def _save_to_cache(self, file_path: str, data: Dict):
        """Saves data to a cache file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f)
        except IOError as e:
            logging.warning(f"Could not write to cache file {file_path}: {e}")
        