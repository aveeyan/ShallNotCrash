# shallnotcrash/path_planner/utils/touchdown.py
"""
Selects the optimal touchdown point on a given landing site.
"""
from typing import List
from ..data_models import Waypoint
from ...landing_site.data_models import LandingSite
from .coordinates import destination_point

# Define the conversion constant for clarity and precision
METERS_TO_FEET = 3.28084

class TouchdownSelector:
    """
    Determines the best physical point to target for landing.
    """
    def get_touchdown_points(self, site: LandingSite, wind_heading_deg: float) -> List[Waypoint]:
        """
        Selects an optimal touchdown point on the landing site. This method is now
        resilient to elevation data being provided in feet or meters.
        """
        # --- PATCH: Robustly determine site elevation in feet ---
        site_elevation_ft = 0.0
        if hasattr(site, 'elevation_ft') and site.elevation_ft is not None:
            site_elevation_ft = site.elevation_ft
        elif hasattr(site, 'elevation_m') and site.elevation_m is not None:
            # Convert from meters to feet if 'elevation_m' is provided
            site_elevation_ft = site.elevation_m * METERS_TO_FEET
            print(f"INFO: TouchdownSelector converted elevation from {site.elevation_m:.1f}m to {site_elevation_ft:.1f}ft.")
        else:
            print("WARNING: TouchdownSelector could not find elevation data for the site. Assuming 0 ft MSL.")
        # --- END PATCH ---

        # Logic for non-runway sites (e.g., roads, fields)
        if site.site_type != "RUNWAY":
            # The target is the center of the site, using the correctly determined elevation.
            return [Waypoint(
                lat=site.lat,
                lon=site.lon,
                alt_ft=site_elevation_ft,
                airspeed_kts=65, # Target approach speed
                notes="FIELD_CENTER"
            )]

        # Logic for official runways
        runway_bearing = site.bearing_deg
        
        # Touchdown point is typically ~1000ft from the threshold.
        touchdown_dist_nm = 1000 / 6076.12

        # Calculate the touchdown point coordinates
        td_lat, td_lon = destination_point(site.lat, site.lon, runway_bearing, touchdown_dist_nm)

        return [Waypoint(
            lat=td_lat,
            lon=td_lon,
            alt_ft=site_elevation_ft, # Use the correctly determined elevation
            airspeed_kts=65,
            notes=f"TOUCHDOWN_ZONE_RWY_{site.designator}"
        )]