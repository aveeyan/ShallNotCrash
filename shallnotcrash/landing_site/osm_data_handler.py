# shallnotcrash/landing_site/osm_data_handler.py
"""
Handles all interactions with the OpenStreetMap (OSM) Overpass API.

This module is responsible for fetching the raw geographical data needed
to identify potential non-runway landing sites.
"""
import logging
import requests
import requests_cache

from .utils.calculations import OverpassQueryBuilder

class OSMDataHandler:
    """
    A dedicated handler for fetching and caching data from the Overpass API.
    """
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, timeout: int, cache_enabled: bool = True):
        """
        Initializes the OSMDataHandler.

        Args:
            timeout: The timeout in seconds for the API request.
            cache_enabled: If True, API requests will be cached to a local
                           file to speed up subsequent identical requests.
        """
        self.timeout = timeout
        if cache_enabled:
            # Install a cache for all requests made by this session object.
            self.session = requests_cache.CachedSession(
                'osm_cache',
                backend='sqlite',
                expire_after=86400  # Cache requests for 24 hours
            )
        else:
            self.session = requests.Session()
        logging.info(f"OSMDataHandler initialized. Cache enabled: {cache_enabled}")

    def fetch_osm_data(self, lat: float, lon: float, radius_km: float) -> list:
        """
        Fetches all relevant OSM 'way' and 'area' elements within a given
        radius of a coordinate.

        Args:
            lat: The latitude of the search center.
            lon: The longitude of the search center.
            radius_km: The search radius in kilometers.

        Returns:
            A list of OSM element dictionaries, or an empty list if the
            request fails.
        """
        query = OverpassQueryBuilder.build_query(lat, lon, radius_km, self.timeout)
        
        try:
            logging.info(f"Sending Overpass API query for ({lat:.4f}, {lon:.4f})...")
            response = self.session.post(self.OVERPASS_URL, data=query, timeout=self.timeout)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            logging.info(f"Successfully received {len(data.get('elements', []))} elements from Overpass API.")
            return data.get('elements', [])
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to fetch data from Overpass API: {e}")
            return []
        except Exception as e:
            logging.error(f"An unexpected error occurred during OSM data fetching: {e}")
            return []