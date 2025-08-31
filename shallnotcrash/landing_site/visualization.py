# shallnotcrash/landing_site/visualization.py
"""
[REFINED VISUALIZATION - V6]
This version uses the accurate geometric data for all sites to draw proper polygons,
removing approximations. It also centralizes utility functions for better maintainability.
"""
import folium
import logging
import math
from folium.plugins import GroupedLayerControl
from typing import Dict, List, Tuple, Union

from ..path_planner.data_models import AircraftState, FlightPath
from .data_models import SearchResults, LandingSite
from .utils.coordinates import CoordinateCalculations # Import for centralized functions

class MapVisualizer:
    """Creates Folium maps that accurately visualize all landing site types as polygons."""
    
    def create_integrated_mission_map(
        self,
        start_state: AircraftState,
        results: SearchResults,
        flight_paths: Dict[int, FlightPath]
    ) -> folium.Map:
        """Generates an integrated mission map with accurate site polygons."""
        map_center = [start_state.lat, start_state.lon]
        mission_map = folium.Map(location=map_center, zoom_start=12, tiles="CartoDB positron")

        logging.info(f"Creating map with {len(results.landing_sites)} landing sites")

        # Mark the aircraft starting point
        folium.Marker(
            location=[start_state.lat, start_state.lon],
            popup=f"<b>Aircraft Start</b><br>Alt: {start_state.alt_ft:.0f} ft<br>Speed: {start_state.airspeed_kts:.0f} kts",
            icon=folium.Icon(color='green', icon='plane', prefix='fa')
        ).add_to(mission_map)

        # Create layer groups for better control
        aviation_group = folium.FeatureGroup(name='Aviation Sites', show=True).add_to(mission_map)
        road_group = folium.FeatureGroup(name='Road Sites', show=True).add_to(mission_map)
        emergency_group = folium.FeatureGroup(name='Emergency Sites', show=True).add_to(mission_map)
        paths_group = folium.FeatureGroup(name='Flight Paths', show=True).add_to(mission_map)

        # Process and visualize each site
        for i, site in enumerate(results.landing_sites):
            logging.debug(f"Visualizing site #{i+1}: {site.site_type}")
            
            # Determine the group and create visuals
            if site.site_type.lower() in ['runway', 'taxiway', 'airfield', 'airstrip']:
                visuals = self._create_site_visuals(site, i + 1, 'blue', 'plane')
                group = aviation_group
            elif site.site_type.lower() in ['major_road', 'highway', 'road']:
                visuals = self._create_site_visuals(site, i + 1, 'orange', 'road')
                group = road_group
            else:
                visuals = self._create_emergency_site_visuals(site, i + 1)
                group = emergency_group

            # Add visuals to the appropriate group
            for visual in visuals:
                visual.add_to(group)

            # Add flight path if it exists for the current site
            if i in flight_paths:
                self._create_path_visual(flight_paths[i]).add_to(paths_group)

        # Add layer control to toggle groups
        folium.LayerControl().add_to(mission_map)
        
        logging.info("Map creation completed successfully.")
        return mission_map

    def _create_site_visuals(self, site: LandingSite, rank: int, color: str, icon_name: str) -> List[Union[folium.Marker, folium.Polygon]]:
        """[NEW] Generic function to create visuals (marker + polygon) for any site."""
        popup_html = self._create_popup_html(site, rank, color)
        
        # Create the center marker for the site
        marker = folium.Marker(
            location=[site.lat, site.lon],
            popup=popup_html,
            tooltip=f"<b>#{rank}: {site.site_type.title()}</b> | Score: {site.suitability_score}",
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        )

        # Always use polygon_coords if available, as it's the most accurate representation
        if site.polygon_coords and len(site.polygon_coords) >= 3:
            coords_to_draw = site.polygon_coords
            # Simplify very large polygons for performance
            if len(coords_to_draw) > 50:
                coords_to_draw = CoordinateCalculations.simplify_polygon(coords_to_draw, tolerance=0.0001)

            polygon = folium.Polygon(
                locations=coords_to_draw,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.4,
                popup=f"#{rank}: {site.site_type.title()}"
            )
            return [marker, polygon]
        
        # Fallback if no valid polygon exists (should be rare with earlier fixes)
        logging.warning(f"Site #{rank} ({site.site_type}) missing valid polygon data. Drawing marker only.")
        return [marker]

    def _create_emergency_site_visuals(self, site: LandingSite, rank: int) -> List[Union[folium.Marker, folium.Polygon]]:
        """Creates visualization for non-road, non-aviation emergency sites (e.g., fields)."""
        color = self._get_color_for_score(site.suitability_score)
        icon = self._get_icon_for_score(site.suitability_score)
        
        # Create visuals using the generic function
        visuals = self._create_site_visuals(site, rank, color, icon)
        
        # Override the marker's icon with the score-based one
        if visuals:
             visuals[0].icon = folium.Icon(color=color, icon=icon, prefix='fa')
        
        return visuals

    def _create_path_visual(self, flight_path: FlightPath) -> folium.PolyLine:
        """Creates a visual line for a flight path."""
        path_points = [(wp.lat, wp.lon) for wp in flight_path.waypoints]
        return folium.PolyLine(
            locations=path_points,
            color='#4A90E2', # A distinct blue for the path
            weight=3,
            opacity=0.9,
            tooltip="Calculated Glide Path"
        )

    def _create_popup_html(self, site: LandingSite, rank: int, color: str) -> str:
        """Creates a standardized, detailed HTML popup for any landing site."""
        icon_map = {
            'runway': '✈️', 'taxiway': '✈️', 'airfield': '✈️', 'airstrip': '✈️',
            'major_road': '🛣️', 'highway': '🛣️', 'road': '🛣️',
        }
        icon = icon_map.get(site.site_type, '⚠️')
        
        return f"""
        <div style="font-family: Arial, sans-serif; width: 320px;">
            <h4 style="margin:0; padding: 5px; background-color:{color}; color:white; border-radius: 3px 3px 0 0;">
                {icon} <b>#{rank}: {site.site_type.replace('_', ' ').title()}</b>
            </h4>
            <div style="padding: 8px;">
                <table style="width:100%; font-size: 13px; border-collapse: collapse;">
                    <tr style="border-bottom: 1px solid #eee;"><td style="padding:4px;"><b>Score</b></td><td>{site.suitability_score} / 100</td></tr>
                    <tr style="border-bottom: 1px solid #eee;"><td style="padding:4px;"><b>Dimensions</b></td><td>{site.length_m:.0f}m × {site.width_m:.0f}m</td></tr>
                    <tr style="border-bottom: 1px solid #eee;"><td style="padding:4px;"><b>Orientation</b></td><td>{site.orientation_degrees:.1f}°</td></tr>
                    <tr style="border-bottom: 1px solid #eee;"><td style="padding:4px;"><b>Surface</b></td><td>{site.surface_type.title()}</td></tr>
                    <tr style="border-bottom: 1px solid #eee;"><td style="padding:4px;"><b>Distance</b></td><td>{site.distance_km:.2f} km</td></tr>
                    <tr style="border-bottom: 1px solid #eee;"><td style="padding:4px;"><b>Risk Level</b></td><td><b>{site.safety_report.risk_level}</b></td></tr>
                </table>
            </div>
        </div>
        """

    def _get_color_for_score(self, score: int) -> str:
        """Determines color based on suitability score for emergency sites."""
        if score >= 85: return 'darkgreen'
        if score >= 70: return 'green'
        if score >= 55: return 'orange'
        return 'red'

    def _get_icon_for_score(self, score: int) -> str:
        """Determines icon based on suitability score for emergency sites."""
        if score >= 70: return 'check'
        return 'exclamation-triangle'

    def save_map(self, mission_map: folium.Map, filename: str):
        """Saves the folium map to an HTML file."""
        try:
            mission_map.save(filename)
            logging.info(f"Mission map saved to {filename}")
        except Exception as e:
            logging.error(f"Failed to save map to {filename}: {e}")
