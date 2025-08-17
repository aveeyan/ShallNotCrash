# shallnotcrash/path_planner/runway_loader.py
"""
Loads potential landing sites from local data files (e.g., CSV).
This provides a reliable, offline-first source of landing options,
decoupling the system from unreliable network APIs.
"""
import csv
from typing import List
# Note the relative import to access the data models from the sibling module
from ..landing_site.data_models import LandingSite

def load_sites_from_csv(file_path: str) -> List[LandingSite]:
    """
    Parses a CSV file and returns a list of LandingSite objects.

    The CSV is expected to have a header and the following columns:
    lat, lon, site_type, description, length_m, orientation_degrees, elevation_m
    """
    sites = []
    print(f"RUNWAY LOADER: Loading sites from local file: {file_path}")
    try:
        with open(file_path, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for i, row in enumerate(reader):
                try:
                    site = LandingSite(
                        lat=float(row['lat']),
                        lon=float(row['lon']),
                        site_type=row.get('site_type', 'UNKNOWN').upper(),
                        description=row.get('description', f'Local Site #{i+1}'),
                        length_m=float(row['length_m']) if row.get('length_m') else None,
                        orientation_degrees=float(row['orientation_degrees']) if row.get('orientation_degrees') else None,
                        elevation_m=float(row['elevation_m']) if row.get('elevation_m') else None,
                        source="LOCAL_CSV"
                    )
                    sites.append(site)
                except (ValueError, KeyError) as e:
                    print(f"RUNWAY LOADER WARNING: Skipping invalid row {i+1} in {file_path}. Error: {e}")
        print(f"RUNWAY LOADER: Successfully loaded {len(sites)} sites.")
        return sites
    except FileNotFoundError:
        print(f"RUNWAY LOADER ERROR: The file {file_path} was not found.")
        return []
