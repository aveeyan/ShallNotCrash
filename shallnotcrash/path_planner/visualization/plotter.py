# shallnotcrash/path_planner/visualization/plotter.py
"""
Contains the PathVisualizer class for generating interactive 2D and 3D maps.
"""
import folium
import plotly.graph_objects as go
from typing import List, Dict
from ..data_models import FlightPath, AircraftState
from ...landing_site.data_models import SearchResults, LandingSite
from ..utils.coordinates import destination_point

class PathVisualizer:
    """Generates interactive maps from a full mission profile."""

    def _calculate_fallback_polygon(self, site: LandingSite) -> List[tuple]:
        """
        FALLBACK ONLY: Creates a rectangular polygon when high-fidelity data is missing.
        """
        # [This function remains unchanged, but is now correctly used as a fallback]
        if not hasattr(site, 'length_m') or not hasattr(site, 'width_m'):
            return []
        
        bearing = getattr(site, 'bearing_deg', 0)
        length_nm = site.length_m / 1852.0
        width_nm = site.width_m / 1852.0
        center_lat, center_lon = site.lat, site.lon
        p_start = destination_point(center_lat, center_lon, bearing + 180, length_nm / 2)
        p_end = destination_point(center_lat, center_lon, bearing, length_nm / 2)
        c1 = destination_point(p_start[0], p_start[1], bearing - 90, width_nm / 2)
        c2 = destination_point(p_start[0], p_start[1], bearing + 90, width_nm / 2)
        c3 = destination_point(p_end[0], p_end[1], bearing + 90, width_nm / 2)
        c4 = destination_point(p_end[0], p_end[1], bearing - 90, width_nm / 2)
        return [c1, c2, c3, c4, c1]

    def create_multi_path_map(
        self,
        start_state: AircraftState,
        search_results: SearchResults,
        flight_paths: Dict[int, FlightPath]
    ) -> folium.Map:
        """
        MODIFIED: Creates a Folium map with a layer for each potential path.
        """
        map_center = [start_state.lat, start_state.lon]
        m = folium.Map(location=map_center, zoom_start=12, tiles="CartoDB positron")

        folium.Marker(
            location=[start_state.lat, start_state.lon],
            popup=f"<b>Start Point</b><br>Alt: {start_state.alt_ft:.0f} ft",
            icon=folium.Icon(color='green', icon='plane', prefix='fa')
        ).add_to(m)

        for i, site in enumerate(search_results.landing_sites):
            if i not in flight_paths:
                continue

            flight_path = flight_paths[i]
            site_label = getattr(site, 'designator', f"{site.site_type.replace('_', ' ').title()} #{i+1}")
            fg = folium.FeatureGroup(name=f"Option {i+1}: {site_label}", show=(i == 0))

            # --- PATCH: Prioritize high-fidelity boundary data ---
            # Check for the precise coordinates from the landing_site module first.
            if hasattr(site, 'boundary_coords') and site.boundary_coords:
                polygon_coords = site.boundary_coords
                print(f"INFO: Using high-fidelity polygon for {site_label}.")
            # If not available, use the runway polygon calculator.
            elif hasattr(site, 'polygon') and site.polygon:
                 polygon_coords = site.polygon
                 print(f"INFO: Using calculated runway polygon for {site_label}.")
            # As a last resort, generate a generic fallback rectangle.
            else:
                polygon_coords = self._calculate_fallback_polygon(site)
                print(f"WARNING: Using low-fidelity fallback polygon for {site_label}.")
            # --- END PATCH ---

            if polygon_coords:
                # Use PolyLine for open shapes (roads) and Polygon for closed shapes (fields)
                if site.site_type in ["MAJOR_ROAD", "MINOR_ROAD", "TAXIWAY"]:
                     folium.PolyLine(
                        locations=polygon_coords,
                        color='red', weight=15, opacity=0.7,
                        popup=f"<b>{site_label}</b><br>Score: {site.suitability_score}"
                    ).add_to(fg)
                else: # For fields or other area-based sites
                    folium.Polygon(
                        locations=polygon_coords,
                        color='red', fill=True, fill_color='red', fill_opacity=0.4,
                        popup=f"<b>{site_label}</b><br>Score: {site.suitability_score}"
                    ).add_to(fg)

            path_points = [(wp.lat, wp.lon) for wp in flight_path.waypoints]
            folium.PolyLine(
                locations=path_points, color='blue', weight=3, opacity=0.8,
                popup=f"Glide Path to {site_label}"
            ).add_to(fg)

            fg.add_to(m)

        folium.LayerControl().add_to(m)
        return m

    # --- [The create_3d_plot and save methods remain unchanged] ---
    def create_3d_plot(self, start_state: AircraftState, search_results: SearchResults, flight_paths: Dict[int, FlightPath]) -> go.Figure:
        # This function is correct and does not need modification.
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(x=[start_state.lon], y=[start_state.lat], z=[start_state.alt_ft], mode='markers', marker=dict(size=10, color='green', symbol='circle'), name='Start Point'))
        for i, site in enumerate(search_results.landing_sites):
            if i not in flight_paths: continue
            path = flight_paths[i]
            site_label = getattr(site, 'designator', f"{site.site_type.replace('_', ' ').title()} #{i+1}")
            lons = [wp.lon for wp in path.waypoints]; lats = [wp.lat for wp in path.waypoints]; alts = [wp.alt_ft for wp in path.waypoints]
            fig.add_trace(go.Scatter3d(x=lons, y=lats, z=alts, mode='lines', line=dict(width=4), name=f'Path to {site_label}'))
            fig.add_trace(go.Scatter3d(x=[lons[-1]], y=[lats[-1]], z=[alts[-1]], mode='markers', marker=dict(size=8, color='red', symbol='cross'), name=f'Target: {site_label}'))
        fig.update_layout(title='3D Emergency Glide Path Visualization', scene=dict(xaxis_title='Longitude', yaxis_title='Latitude', zaxis_title='Altitude (ft MSL)', aspectratio=dict(x=1, y=1, z=0.5)), margin=dict(r=20, l=10, b=10, t=40))
        return fig

    def save_map(self, m: folium.Map, filename: str) -> None:
        m.save(filename)
        print(f"\n-> Interactive 2D map generated: '{filename}'.")

    def save_3d_plot(self, fig: go.Figure, filename: str) -> None:
        fig.write_html(filename)
        print(f"-> Interactive 3D plot generated: '{filename}'.")