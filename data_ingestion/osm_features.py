"""
data_ingestion/osm_features.py
──────────────────────────────
Uses OSMnx to download building footprints and road networks for a given
region and persist them as GeoJSON files.
"""

import os
import geopandas as gpd
import osmnx as ox
from shapely.geometry import box


class OSMDownloadError(Exception):
    """Raised when an OSMnx query returns no data or fails."""
    pass


# ---------------------------------------------------------------------------
# Building footprints
# ---------------------------------------------------------------------------

def fetch_building_footprints(
    bounds: tuple[float, float, float, float],
    output_path: str = "buildings.geojson",
) -> gpd.GeoDataFrame:
    """
    Download building footprints from OpenStreetMap for a bounding box.

    Parameters
    ----------
    bounds : tuple[float, float, float, float]
        ``(west, south, east, north)`` in WGS-84 degrees.
    output_path : str
        Destination GeoJSON file path.

    Returns
    -------
    geopandas.GeoDataFrame
        Building footprints with geometry and available OSM tags.

    Raises
    ------
    OSMDownloadError
        If no buildings are found in the specified region.
    """
    west, south, east, north = bounds
    polygon = box(west, south, east, north)

    try:
        buildings = ox.features_from_polygon(
            polygon,
            tags={"building": True},
        )
    except Exception as exc:
        raise OSMDownloadError(
            f"Failed to download building footprints: {exc}"
        ) from exc

    if buildings.empty:
        raise OSMDownloadError(
            f"No building footprints found within bounds {bounds}."
        )

    # Keep only polygon / multipolygon geometries (drop nodes)
    buildings = buildings[
        buildings.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ].copy()

    if buildings.empty:
        raise OSMDownloadError(
            "Building data was returned but contained no polygon geometries."
        )

    # Ensure CRS is WGS-84
    if buildings.crs is None:
        buildings = buildings.set_crs(epsg=4326)

    # Persist to disk
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    buildings.to_file(output_path, driver="GeoJSON")
    print(
        f"[OSM] {len(buildings)} building footprints saved to "
        f"{os.path.abspath(output_path)}"
    )
    return buildings


# ---------------------------------------------------------------------------
# Road network
# ---------------------------------------------------------------------------

def fetch_road_network(
    bounds: tuple[float, float, float, float],
    network_type: str = "drive",
    output_path: str = "roads.geojson",
) -> gpd.GeoDataFrame:
    """
    Download the road network from OpenStreetMap for a bounding box.

    Parameters
    ----------
    bounds : tuple[float, float, float, float]
        ``(west, south, east, north)`` in WGS-84 degrees.
    network_type : str
        OSMnx network type — ``"drive"``, ``"walk"``, ``"bike"``, or ``"all"``
        (default ``"drive"``).
    output_path : str
        Destination GeoJSON file path for the edges (road segments).

    Returns
    -------
    geopandas.GeoDataFrame
        Road network edges with geometry and OSM attributes.

    Raises
    ------
    OSMDownloadError
        If no roads are found in the specified region.
    """
    west, south, east, north = bounds
    polygon = box(west, south, east, north)

    try:
        graph = ox.graph_from_polygon(
            polygon,
            network_type=network_type,
            simplify=True,
        )
    except Exception as exc:
        raise OSMDownloadError(
            f"Failed to download road network: {exc}"
        ) from exc

    # Convert graph edges to GeoDataFrame
    edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)

    if edges.empty:
        raise OSMDownloadError(
            f"No road edges found within bounds {bounds} "
            f"for network type '{network_type}'."
        )

    # Persist to disk
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    edges.to_file(output_path, driver="GeoJSON")
    print(
        f"[OSM] {len(edges)} road segments ({network_type}) saved to "
        f"{os.path.abspath(output_path)}"
    )
    return edges


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Quick smoke-test: small area in Bengaluru
    roi_bounds = (77.58, 12.95, 77.62, 12.99)

    print("— Fetching building footprints —")
    buildings_gdf = fetch_building_footprints(
        roi_bounds,
        output_path="output/buildings.geojson",
    )
    print(f"  Columns: {list(buildings_gdf.columns[:10])} ...")

    print("\n— Fetching road network —")
    roads_gdf = fetch_road_network(
        roi_bounds,
        network_type="drive",
        output_path="output/roads.geojson",
    )
    print(f"  Columns: {list(roads_gdf.columns[:10])} ...")
