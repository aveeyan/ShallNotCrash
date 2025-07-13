# shallnotcrash/landing_site/visualization.py
"""
Generates the final interactive tactical map for visualizing landing site
search results. This module prioritizes clarity and situational awareness.
"""
import folium
import logging

from .data_models import SearchResults

class MapVisualizer:
    """
    Creates a Folium map with all necessary tactical overlays.
    """
    def create_map(self, results: SearchResults) -> folium.Map:
        """
        Creates a folium map object from the search results.

        This has been enhanced to include a visual representation of the
        search radius for improved situational awareness.
        """
        origin_lat = results.origin_airport.lat
        origin_lon = results.origin_airport.lon
        
        site_map = folium.Map(location=[origin_lat, origin_lon], zoom_start=10)
        
        # --- STRATEGIC ENHANCEMENT ---
        # Add a large, semi-transparent circle to clearly denote the search radius.
        # This provides immediate context for the operational area.
        search_radius_m = results.search_parameters.get('search_radius_km', 20) * 1000
        folium.Circle(
            location=[origin_lat, origin_lon],
            radius=search_radius_m,
            color='#3498db',
            fill=True,
            fill_color='#3498db',
            fill_opacity=0.05,
            weight=1,
            popup=f"Search Radius: {search_radius_m / 1000} km"
        ).add_to(site_map)

        # Mark the point of origin (the aircraft's position).
        folium.Marker(
            [origin_lat, origin_lon],
            popup="Search Origin",
            icon=folium.Icon(color="blue", icon="plane")
        ).add_to(site_map)

        # Add each identified landing site to the map.
        for site in results.landing_sites:
            color = self._get_color_for_score(site.suitability_score)
            popup_html = self._create_popup_html(site)
            
            # --- PROTOCOL CORRECTION ---
            # GeoJSON requires coordinates in (longitude, latitude) order.
            # The polygon also needs to be nested in an extra list for GeoJSON spec.
            geojson_coords = [[(lon, lat) for lat, lon in site.polygon_coords]]
            
            folium.GeoJson(
                {"type": "Polygon", "coordinates": geojson_coords},
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': color,
                    'weight': 2,
                    'fillOpacity': 0.5 # Use semi-transparency for clarity
                },
                popup=folium.Popup(popup_html, max_width=350)
            ).add_to(site_map)
        
        return site_map

    def save_map(self, site_map: folium.Map, filename: str):
        """Saves the folium map to an HTML file."""
        site_map.save(filename)
        logging.info(f"Tactical map has been generated and saved to {filename}")

    def _get_color_for_score(self, score: int) -> str:
        """Returns a color based on the site's suitability score."""
        if score > 85: return 'green'
        if score > 60: return 'orange'
        return 'red'

    def _create_popup_html(self, site) -> str:
        """Creates a rich HTML popup for a landing site."""
        # Display the specific risk level from the new analyzer.
        safety_details = f"<b>Safety: {site.safety_report.safety_score}/100 ({site.safety_report.risk_level})</b>"
        
        return f"""
        <h4>{site.site_type.replace('_', ' ').title()}</h4>
        <hr style="margin: 5px 0;">
        <b>Suitability Score: {site.suitability_score}/100</b><br>
        {safety_details}<br>
        <b>Dimensions:</b> {site.length_m}m x {site.width_m}m<br>
        <b>Surface:</b> {site.surface_type.title()}<br>
        <b>Distance:</b> {site.distance_km:.2f} km
        """