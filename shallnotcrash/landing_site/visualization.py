# shallnotcrash/landing_site/visualization.py
"""
Generates the final interactive tactical map for visualizing landing site
search results. This module prioritizes clarity and situational awareness.
"""
import folium
import logging
from folium.plugins import GroupedLayerControl

from .data_models import SearchResults, LandingSite

class MapVisualizer:
    """
    Creates a Folium map with all necessary tactical overlays.
    This has been upgraded with a corrected layering system (radio buttons) and 
    a precise, score-based color scheme.
    """
    def create_map(self, results: SearchResults) -> folium.Map:
        """
        Creates a folium map object from the search results.
        The map now includes correctly functioning radio buttons for layer selection
        and colors sites based on a granular suitability score.
        """
        origin_lat = results.origin_airport.lat
        origin_lon = results.origin_airport.lon
        
        site_map = folium.Map(location=[origin_lat, origin_lon], zoom_start=9)
        
        folium.Circle(
            location=[origin_lat, origin_lon],
            radius=results.search_parameters.get('search_radius_km', 20) * 1000,
            color='#3498db', fill=True, fill_color='#3498db', fill_opacity=0.05, weight=1
        ).add_to(site_map)

        folium.Marker(
            [origin_lat, origin_lon],
            popup="Search Origin",
            icon=folium.Icon(color="blue", icon="plane", prefix='glyphicon')
        ).add_to(site_map)

        # --- PROTOCOL REBUILT: Layering Logic ---
        # The layers are now populated inclusively. An object that is in "Top 3"
        # is also created in "Top 5" and "All Sites". This ensures the radio
        # buttons function as the user expects.
        # Default view is set to "Top 5 Sites" for immediate tactical relevance.
        top_3_group = folium.FeatureGroup(name='Top 3 Sites', show=False).add_to(site_map)
        top_5_group = folium.FeatureGroup(name='Top 5 Sites', show=True).add_to(site_map)
        all_sites_group = folium.FeatureGroup(name='All Sites', show=False).add_to(site_map)

        for i, site in enumerate(results.landing_sites):
            # A site must be added to every layer it qualifies for. Since a folium
            # object can only have one parent, we must create distinct copies for each layer.
            
            # Add to "All Sites" layer
            marker_all, polygon_all = self._create_site_visuals(site, i + 1)
            marker_all.add_to(all_sites_group)
            polygon_all.add_to(all_sites_group)

            # Add to "Top 5" layer if applicable
            if i < 5:
                marker_5, polygon_5 = self._create_site_visuals(site, i + 1)
                marker_5.add_to(top_5_group)
                polygon_5.add_to(top_5_group)

            # Add to "Top 3" layer if applicable
            if i < 3:
                marker_3, polygon_3 = self._create_site_visuals(site, i + 1)
                marker_3.add_to(top_3_group)
                polygon_3.add_to(top_3_group)
        
        GroupedLayerControl(
            groups={'View Options': [top_3_group, top_5_group, all_sites_group]},
            exclusive_groups=True,
            collapsed=False
        ).add_to(site_map)
        
        return site_map

    def save_map(self, site_map: folium.Map, filename: str):
        """Saves the folium map to an HTML file."""
        site_map.save(filename)
        logging.info(f"Tactical map has been generated and saved to {filename}")

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

        geojson_coords = [[(lon, lat) for lat, lon in site.polygon_coords]]
        polygon = folium.GeoJson(
            {"type": "Polygon", "coordinates": geojson_coords},
            style_function=lambda x, color=color: {
                'fillColor': color, 'color': color, 'weight': 2, 'fillOpacity': 0.4
            }
        )
        return marker, polygon

    def _get_color_for_score(self, site_type: str, score: int) -> str:
        """
        Returns a color based on the new tactical score hierarchy.
        The logic is now a strict if/elif/else chain to prevent ambiguity.
        """
        if 'runway' in site_type or 'airport' in site_type:
            return '#3498db'  # Blue for all official runways/airports
        elif score >= 90:
            return '#2ecc71'  # Dark Green
        elif score >= 80:
            return '#82e0aa'  # Lime Green
        elif score >= 70:
            return '#f1c40f'  # Yellow/Orange
        elif score >= 60:
            return '#e67e22'  # Orange/Red
        else:
            return '#c0392b'  # Red

    def _get_icon_for_site(self, site_type: str, score: int) -> folium.Icon:
        """Returns a specific icon for each type of landing site."""
        if 'runway' in site_type or 'airport' in site_type:
            return folium.Icon(color='blue', icon='plane', prefix='glyphicon')
        
        color_map = {
            90: 'darkgreen', 80: 'green', 70: 'orange', 60: 'lightred'
        }
        icon_color = 'red'
        for threshold, color in color_map.items():
            if score >= threshold:
                icon_color = color
                break

        return folium.Icon(color=icon_color, icon='road', prefix='glyphicon')


    def _create_popup_html(self, site: LandingSite, rank: int, color: str) -> str:
        """Creates a rich, well-described HTML popup for a landing site."""
        return f"""
        <div style="font-family: monospace; width: 350px;">
            <h4 style="border-left: 5px solid {color}; padding-left: 10px;">
                <b>#{rank} | {site.suitability_score} | {site.site_type.replace('_', ' ').title()}</b>
            </h4>
            <hr style="margin: 5px 0;">
            <table style="width:100%; font-size: 13px;">
                <tr><td style="width:120px;"><b>Status</b></td><td>{site.safety_report.risk_level}</td></tr>
                <tr><td><b>Dimensions</b></td><td>{site.length_m}m x {site.width_m}m</td></tr>
                <tr><td><b>Surface</b></td><td>{site.surface_type.title()}</td></tr>
                <tr><td><b>Distance</b></td><td>{site.distance_km:.2f} km</td></tr>
            </table>
        </div>
        """