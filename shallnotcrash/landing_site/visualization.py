# shallnotcrash/landing_site/visualization.py
"""
[INTERACTIVE VISUALIZATION - V8 - ROBUST]
This version uses a simpler, more robust layering strategy to ensure all
flight path options are correctly rendered and toggleable in the map's
layer control.
"""
import folium
import logging
from typing import Dict, List, Tuple, Union

from ..path_planner.data_models import AircraftState, FlightPath
from .data_models import SearchResults, LandingSite

class MapVisualizer:
    """Creates interactive Folium maps with a simple, robust layer for each path."""
    
    def create_integrated_mission_map(
        self,
        start_state: AircraftState,
        results: SearchResults,
        flight_paths: Dict[int, FlightPath]
    ) -> folium.Map:
        """
        Generates an interactive map with a dedicated layer for each flight path.
        """
        map_center = [start_state.lat, start_state.lon]
        mission_map = folium.Map(location=map_center, zoom_start=11, tiles="CartoDB positron")

        # --- Layer for the aircraft's start position ---
        start_group = folium.FeatureGroup(name="Aircraft Start Position (Point A)", show=True).add_to(mission_map)
        folium.Marker(
            location=[start_state.lat, start_state.lon],
            popup="<b>Aircraft Start (Point A)</b>",
            tooltip="Aircraft Start Position",
            icon=folium.Icon(color='green', icon='plane', prefix='fa')
        ).add_to(start_group)
        
        # --- A single layer for all the landing sites ---
        sites_group = folium.FeatureGroup(name="All Landing Sites", show=True).add_to(mission_map)
        for i, site in enumerate(results.landing_sites):
            visuals = self._create_site_visuals(site, i + 1)
            for visual in visuals:
                visual.add_to(sites_group)

        # --- [THE FIX] Create a separate, hidden layer for EACH flight path ---
        for i, flight_path in flight_paths.items():
            site = results.landing_sites[i]
            path_name = f"Path to Site #{i+1}: {site.site_type.title()}"
            
            # Create a unique FeatureGroup for each path, initially hidden
            path_group = folium.FeatureGroup(name=path_name, show=False).add_to(mission_map)
            self._create_path_visual(flight_path, i + 1).add_to(path_group)

        folium.LayerControl(collapsed=False).add_to(mission_map)
        logging.info("Robust interactive map creation completed successfully.")
        return mission_map

    # --- (Helper methods below are unchanged) ---

    def _create_site_visuals(self, site: LandingSite, rank: int) -> List[Union[folium.Marker, folium.Polygon]]:
        popup_html = self._create_popup_html(site, rank)
        if site.site_type in ['runway', 'taxiway']:
            color, icon = 'blue', 'plane'
        elif 'road' in site.site_type:
            color, icon = 'orange', 'road'
        else:
            color, icon = 'darkred', 'exclamation-triangle'
            
        marker = folium.Marker(location=[site.lat, site.lon], popup=popup_html,
                               tooltip=f"<b>#{rank}: {site.site_type.title()}</b>",
                               icon=folium.Icon(color=color, icon=icon, prefix='fa'))
                               
        if site.polygon_coords and len(site.polygon_coords) >= 3:
            polygon = folium.Polygon(locations=site.polygon_coords, color=color, fill=True, fill_color=color, fill_opacity=0.4)
            return [marker, polygon]
        return [marker]
        
    def _create_path_visual(self, flight_path: FlightPath, rank: int) -> folium.PolyLine:
        path_points = [(wp.lat, wp.lon) for wp in flight_path.waypoints]
        return folium.PolyLine(locations=path_points, color='#E41A1C', weight=3, opacity=0.9,
                               tooltip=f"Calculated Glide Path to Site #{rank}")
                               
    def _create_popup_html(self, site: LandingSite, rank: int) -> str:
        return f"""
        <b>#{rank}: {site.site_type.replace('_', ' ').title()}</b><br>
        Score: {site.suitability_score}<br>
        Dimensions: {site.length_m:.0f}m x {site.width_m:.0f}m<br>
        Risk: {site.safety_report.risk_level}
        """
