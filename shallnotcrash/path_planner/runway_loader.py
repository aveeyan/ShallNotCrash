# shallnotcrash/landing_site/runway_loader.py
"""
[REWORKED FOR PERFORMANCE]
Loads runway data from OpenStreetMap, using a robust local caching
mechanism to avoid slow network requests on every run.
"""
import requests
import json
import sqlite3
import time
import os
from typing import List, Dict, Any, Optional

# --- Constants ---
OVERPASS_URL = "http://overpass-api.de/api/interpreter"
CACHE_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'osm_cache.sqlite')
CACHE_EXPIRY_SECONDS = 7 * 24 * 60 * 60  # Cache data for 7 days

class RunwayLoader:
    """Manages the fetching and caching of runway data from OSM."""

    def __init__(self):
        self._initialize_cache()

    def _initialize_cache(self):
        """Ensures the cache database and table exist."""
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runway_cache (
                    query_hash TEXT PRIMARY KEY,
                    timestamp INTEGER,
                    data TEXT
                )
            """)
            conn.commit()

    def _is_cache_valid(self, query_hash: str) -> bool:
        """Checks if a non-expired cache entry exists for the query."""
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT timestamp FROM runway_cache WHERE query_hash = ?", (query_hash,))
            result = cursor.fetchone()
            if result:
                cache_time = result[0]
                if (time.time() - cache_time) < CACHE_EXPIRY_SECONDS:
                    return True
        return False

    def _load_from_cache(self, query_hash: str) -> Optional[List[Dict[str, Any]]]:
        """Loads runway data from the SQLite cache."""
        print("...Loading runways from local cache (fast).")
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data FROM runway_cache WHERE query_hash = ?", (query_hash,))
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
        return None

    def _save_to_cache(self, query_hash: str, data: List[Dict[str, Any]]):
        """Saves runway data to the SQLite cache."""
        print("...Saving new runway data to local cache for future use.")
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO runway_cache (query_hash, timestamp, data) VALUES (?, ?, ?)",
                (query_hash, int(time.time()), json.dumps(data))
            )
            conn.commit()

    def _fetch_from_overpass_api(self, lat: float, lon: float, radius_m: int) -> List[Dict[str, Any]]:
        """Performs the live network query to the Overpass API."""
        print("...No valid cache found. Fetching live runway data from OSM (this may be slow)...")
        
        overpass_query = f"""
        [out:json][timeout:60];
        (
          way["aeroway"="runway"](around:{radius_m},{lat},{lon});
          relation["aeroway"="runway"](around:{radius_m},{lat},{lon});
        );
        out body;
        >;
        out skel qt;
        """
        try:
            response = requests.get(OVERPASS_URL, params={'data': overpass_query})
            response.raise_for_status()
            return response.json().get('elements', [])
        except requests.RequestException as e:
            print(f"! NETWORK ERROR: Could not fetch runway data from Overpass API: {e}")
            return []

    def get_runways(self, lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
        """
        Primary method to get runway data.
        It uses the cache first and falls back to a live query if needed.
        """
        radius_m = radius_km * 1000
        # Create a simple hash of the query parameters to use as a cache key
        query_hash = f"runways_{lat:.4f}_{lon:.4f}_{radius_km}"

        if self._is_cache_valid(query_hash):
            return self._load_from_cache(query_hash)
        else:
            data = self._fetch_from_overpass_api(lat, lon, radius_m)
            if data:
                self._save_to_cache(query_hash, data)
            return data
    