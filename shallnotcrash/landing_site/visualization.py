# shallnotcrash/landing_site/visualization.py
"""
Generates the final interactive tactical map for visualizing an integrated
mission profile, including landing sites and flight paths.
This module is now the central point for 2D mission visualization.
"""
import folium
import logging
from folium.plugins import GroupedLayerControl
from typing import Dict

# --- COMMAND-DIRECTED ARCHITECTURAL COMPROMISE ---
# Importing from path_planner creates a circular dependency, as path_planner
# depends on landing_site. This is a necessary compromise to consolidate
# all visualization logic into this single module as per the directive.
from ..path_planner.data_models import AircraftState, FlightPath
# --- END COMPROMISE ---

from .data_models import SearchResults, LandingSite

class MapVisualizer:
    """
    Creates a Folium map with all necessary tactical overlays, including
    landing sites and calculated flight paths.
    """
    def create_integrated_mission_map(
        self,
        start_state: AircraftState,
        results: SearchResults,
        flight_paths: Dict[int, FlightPath]
    ) -> folium.Map:
        """
        UPGRADED: Creates a single, unified folium map object for the entire mission.
        """
        map_center = [start_state.lat, start_state.lon]
        mission_map = folium.Map(location=map_center, zoom_start=12, tiles="CartoDB positron")

        # Mark the true aircraft starting point
        folium.Marker(
            location=[start_state.lat, start_state.lon],
            popup=f"<b>Aircraft Start</b><br>Alt: {start_state.alt_ft:.0f} ft",
            icon=folium.Icon(color='green', icon='plane', prefix='fa')
        ).add_to(mission_map)

        # Layering logic remains, but will now contain paths as well
        top_3_group = folium.FeatureGroup(name='Top 3 Options', show=False).add_to(mission_map)
        top_5_group = folium.FeatureGroup(name='Top 5 Options', show=True).add_to(mission_map)
        all_sites_group = folium.FeatureGroup(name='All Options', show=False).add_to(mission_map)

        for i, site in enumerate(results.landing_sites):
            # Create visuals for the landing site itself
            marker, polygon = self._create_site_visuals(site, i + 1)
            
            # Create visual for the flight path, if one exists for this site
            path_line = None
            if i in flight_paths:
                path_line = self._create_path_visual(flight_paths[i])

            # Add visuals to the appropriate layers
            # Add to "All Sites" layer
            marker.add_to(all_sites_group)
            polygon.add_to(all_sites_group)
            if path_line: path_line.add_to(all_sites_group)

            # Add to "Top 5" layer if applicable (requires creating new objects)
            if i < 5:
                marker_5, polygon_5 = self._create_site_visuals(site, i + 1)
                marker_5.add_to(top_5_group)
                polygon_5.add_to(top_5_group)
                if i in flight_paths:
                    self._create_path_visual(flight_paths[i]).add_to(top_5_group)

            # Add to "Top 3" layer if applicable
            if i < 3:
                marker_3, polygon_3 = self._create_site_visuals(site, i + 1)
                marker_3.add_to(top_3_group)
                polygon_3.add_to(top_3_group)
                if i in flight_paths:
                    self._create_path_visual(flight_paths[i]).add_to(top_3_group)
        
        GroupedLayerControl(
            groups={'View Options': [top_3_group, top_5_group, all_sites_group]},
            exclusive_groups=True,
            collapsed=False
        ).add_to(mission_map)
        
        return mission_map

    def save_map(self, mission_map: folium.Map, filename: str):
        """Saves the folium map to an HTML file."""
        mission_map.save(filename)
        logging.info(f"Integrated mission map has been generated and saved to {filename}")

    def _create_path_visual(self, flight_path: FlightPath) -> folium.PolyLine:
        """NEW: Creates a visual line for a single flight path."""
        path_points = [(wp.lat, wp.lon) for wp in flight_path.waypoints]
        return folium.PolyLine(
            locations=path_points,
            color='blue',
            weight=3,
            opacity=0.8,
            popup="Calculated Glide Path"
        )

    # --- [Existing helper methods for site visualization remain unchanged] ---
    def _create_site_visuals(self, site: LandingSite, rank: int) -> tuple:
        """Creates a marker and polygon for a single landing site."""
        color = self._get_color_for_score(site.site_type, site.suitability_score)
        icon = self._get_icon_for_site(site.site_type, site.suitability_score)
        popup_html = self._create_popup_html(site, rank, color)
        
        marker = folium.Marker(
            location=[site.lat, site.lon],
            popup=folium.Popup(popup_html, max_width=400),
            tooltip=f"<b>#{rank}: {site.site_type.replace('_', ' ').title()}</b><br>Score: {site.suitability_score}",
            icon=icon
        )

        # Use high-fidelity polygon_coords if available
        if hasattr(site, 'polygon_coords') and site.polygon_coords:
             # folium.Polygon expects a list of (lat, lon) tuples
            polygon = folium.Polygon(
                locations=site.polygon_coords,
                color=color, fill=True, fill_color=color, fill_opacity=0.4
            )
        else:
            # Create a dummy polygon object if no coords are found to avoid errors
            polygon = folium.FeatureGroup()

        return marker, polygon

    def _get_color_for_score(self, site_type: str, score: int) -> str:
        # This function is unchanged
        if 'runway' in site_type.lower() or 'airport' in site_type.lower(): return '#3498db'
        elif score >= 90: return '#2ecc71'
        elif score >= 80: return '#82e0aa'
        elif score >= 70: return '#f1c40f'
        elif score >= 60: return '#e67e22'
        else: return '#c0392b'

    def _get_icon_for_site(self, site_type: str, score: int) -> folium.Icon:
        # This function is unchanged
        if 'runway' in site_type.lower() or 'airport' in site_type.lower():
            return folium.Icon(color='blue', icon='plane', prefix='fa')
        color_map = {90: 'darkgreen', 80: 'green', 70: 'orange', 60: 'lightred'}
        icon_color = 'red'
        for threshold, color in color_map.items():
            if score >= threshold:
                icon_color = color; break
        return folium.Icon(color=icon_color, icon='road', prefix='fa')

    def _create_popup_html(self, site: LandingSite, rank: int, color: str) -> str:
        # This function is unchanged
        return f"""<div style="font-family: monospace; width: 350px;"><h4 style="border-left: 5px solid {color}; padding-left: 10px;"><b>#{rank} | {site.suitability_score} | {site.site_type.replace('_', ' ').title()}</b></h4><hr style="margin: 5px 0;"><table style="width:100%; font-size: 13px;"><tr><td style="width:120px;"><b>Status</b></td><td>{site.safety_report.risk_level}</td></tr><tr><td><b>Dimensions</b></td><td>{site.length_m}m x {site.width_m}m</td></tr><tr><td><b>Surface</b></td><td>{site.surface_type.title()}</td></tr><tr><td><b>Distance</b></td><td>{site.distance_km:.2f} km</td></tr></table></div>"""