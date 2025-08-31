# shallnotcrash/path_planner/non_runway_finder.py
"""
[HIGH-SPEED OFFLINE SITE FINDER - V3.3 - FINAL]
This definitive version corrects the TypeError by using a universally
compatible method for bounding box filtering inside the Osmium handler,
removing the unsupported 'bbox' keyword argument from the apply_file call.
"""
import os
import logging
import math
from typing import List, Dict, Any, Tuple

import osmium
import rasterio
import numpy as np
from shapely.geometry import Polygon, Point, LineString

# --- (Constants are the same) ---
CESSNA_172P_PROFILE = {"min_length_m": 400, "min_width_m": 8, "max_slope_deg": 2.0}
CANDIDATE_TAGS = {
    'highway': {'motorway', 'trunk', 'primary', 'secondary'},
    'landuse': {'farmland', 'meadow', 'grass'},
}
OBSTACLE_TAGS = {'building': None, 'power': {'line', 'tower', 'pole'}, 'natural': {'tree', 'wood'}}
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class OSMFilterHandler(osmium.SimpleHandler):
    """
    [CORRECTED] This handler now performs its own bounding box check, which is
    compatible with all versions of the pyosmium library.
    """
    def __init__(self, bbox: Tuple[float, float, float, float]):
        super().__init__()
        self.bbox = bbox
        self.candidates, self.obstacles, self.processed_ids = [], [], set()

    def _process_feature(self, elem, geom_type: str):
        if elem.id in self.processed_ids: return
        try:
            # Perform the bounding box check manually for universal compatibility.
            if not elem.bounds or not (
                self.bbox[0] < elem.bounds.bottom_right.lon and self.bbox[2] > elem.bounds.top_left.lon and
                self.bbox[1] < elem.bounds.top_left.lat and self.bbox[3] > elem.bounds.bottom_right.lat):
                return

            tags = {tag.k: tag.v for tag in elem.tags}
            is_candidate = any(k in CANDIDATE_TAGS and tags.get(k) in CANDIDATE_TAGS.get(k, {}) for k in tags)
            is_obstacle = any(k in OBSTACLE_TAGS and (OBSTACLE_TAGS.get(k) is None or tags.get(k) in OBSTACLE_TAGS.get(k, {})) for k in tags)

            if is_candidate or is_obstacle:
                nodes = elem.nodes if geom_type == 'way' else elem.outer_rings()[0].nodes
                if len(nodes) < 2: return
                coords = [(n.lon, n.lat) for n in nodes]
                feature = {'id': elem.id, 'type': geom_type, 'tags': tags, 'coords': coords, 'is_closed': elem.is_closed()}
                if is_candidate: self.candidates.append(feature)
                if is_obstacle: self.obstacles.append(feature)
                self.processed_ids.add(elem.id)
        except Exception:
            pass

    def way(self, w): self._process_feature(w, 'way')
    def area(self, a): self._process_feature(a, 'area')


class OfflineSiteFinder:
    def __init__(self, osm_pbf_path: str, dem_dir_path: str):
        if not os.path.exists(osm_pbf_path): raise FileNotFoundError(f"OSM PBF file not found: {osm_pbf_path}")
        if not os.path.isdir(dem_dir_path): raise NotADirectoryError(f"DEM directory not found: {dem_dir_path}")
        self.osm_pbf_path, self.dem_dir_path = osm_pbf_path, dem_dir_path
        self.dem_sources = [rasterio.open(os.path.join(dem_dir_path, f)) for f in os.listdir(dem_dir_path) if f.endswith('.tif')]
        if not self.dem_sources: raise FileNotFoundError(f"No DEM (.tif) files found in {dem_dir_path}")
        logging.info(f"Initialized with {len(self.dem_sources)} DEM files.")

    def find_sites(self, lat: float, lon: float, radius_km: int, profile: Dict = CESSNA_172P_PROFILE) -> List[Dict]:
        logging.info(f"Starting offline search at ({lat:.4f}, {lon:.4f}) with a {radius_km}km radius.")
        
        lat_rad = math.radians(lat)
        deg_lat_radius = radius_km / 111.32
        deg_lon_radius = radius_km / (111.32 * math.cos(lat_rad))
        bbox = (lon - deg_lon_radius, lat - deg_lat_radius, lon + deg_lon_radius, lat + deg_lat_radius)
        
        # [CORRECTED] Instantiate the handler with the bbox and use the simple apply_file call.
        handler = OSMFilterHandler(bbox)
        handler.apply_file(self.osm_pbf_path, locations=True)
        
        candidates, obstacles = handler.candidates, handler.obstacles
        logging.info(f"Found {len(candidates)} potential candidates and {len(obstacles)} obstacles in the region.")
        
        valid_sites = []
        for cand in candidates:
            coords = cand['coords']
            if cand['is_closed'] and len(coords) < 3: continue
            
            geom = Polygon(coords) if cand['is_closed'] else LineString(coords)
            length, width = self._get_dimensions(coords)
            
            if length < profile['min_length_m'] or width < profile['min_width_m']: continue
            
            slope = self._get_slope_for_geom(geom)
            if slope is None or slope > profile['max_slope_deg']: continue

            check_geom = geom.buffer(width / (2 * 111320)) if not cand['is_closed'] else geom
            if not self._is_clear_of_obstacles(check_geom, obstacles): continue
            
            valid_sites.append({'center_lon': geom.centroid.x, 'center_lat': geom.centroid.y,
                                'length_m': length, 'width_m': width, 'slope_deg': slope, 'tags': cand['tags']})
        
        logging.info(f"Found {len(valid_sites)} valid non-runway landing sites.")
        return sorted(valid_sites, key=lambda s: s['length_m'], reverse=True)

    # --- (The rest of the OfflineSiteFinder class is unchanged) ---
    def _get_dimensions(self, coords: List[Tuple[float, float]]) -> Tuple[float, float]:
        if len(coords) < 2: return 0, 0
        mean_lat = np.mean([c[1] for c in coords])
        coords_m = np.array([((c[0] - coords[0][0]) * 111320 * np.cos(np.radians(mean_lat)),
                              (c[1] - coords[0][1]) * 111320) for c in coords])
        if coords_m.shape[0] < 2: return 0, 0
        coords_m -= np.mean(coords_m, axis=0)
        if coords_m.shape[0] < 2: return np.linalg.norm(coords_m), 8
        cov = np.cov(coords_m, rowvar=False)
        _, evecs = np.linalg.eigh(cov)
        proj = coords_m.dot(evecs)
        span = np.max(proj, axis=0) - np.min(proj, axis=0)
        is_line = coords[0] != coords[-1]
        width = 8 if is_line else span[0]
        return span[1], width

    def _get_slope_for_geom(self, geom: any) -> float:
        try:
            line = geom.exterior if hasattr(geom, 'exterior') else geom
            points = [line.interpolate(i, normalized=True) for i in np.linspace(0, 1, 10)]
            coords_to_sample = [(p.x, p.y) for p in points]
            elevations = []
            for src in self.dem_sources:
                for val in src.sample(coords_to_sample):
                    if val[0] > -1000: elevations = val; break
                if len(elevations) > 0: break
            if len(elevations) < 2: return None
            max_e, min_e = np.max(elevations), np.min(elevations)
            p_min, p_max = points[np.argmin(elevations)], points[np.argmax(elevations)]
            dist_m = p_min.distance(p_max) * 111320
            if dist_m == 0: return 0.0
            return np.degrees(np.arctan((max_e - min_e) / dist_m))
        except Exception: return None

    def _is_clear_of_obstacles(self, site_geom: any, obstacles: List[Dict]) -> bool:
        for obs in obstacles:
            obs_geom = Polygon(obs['coords']) if obs['is_closed'] else Point(obs['coords'][0])
            if site_geom.intersects(obs_geom): return False
        return True
    
    def close(self):
        for src in self.dem_sources: src.close()
        logging.info("DEM sources closed.")
