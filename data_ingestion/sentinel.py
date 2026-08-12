"""
data_ingestion/sentinel.py
──────────────────────────
Authenticates with Google Earth Engine, fetches Sentinel-2 L2A surface
reflectance imagery, filters by cloud cover, computes NDVI, and returns
a median composite.  Includes a geemap-based GeoTIFF export helper.
"""

import ee
import geemap
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

GEE_PROJECT_ID = os.getenv("GEE_PROJECT_ID")


class GEEAuthenticationError(Exception):
    """Raised when Google Earth Engine authentication fails."""
    pass


class EmptyCollectionError(Exception):
    """Raised when the filtered image collection contains zero images."""
    pass


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def authenticate_gee() -> None:
    """
    Initialise the Earth Engine API using the project ID from .env.

    Raises
    ------
    GEEAuthenticationError
        If GEE_PROJECT_ID is missing or if ``ee.Initialize`` fails.
    """
    if not GEE_PROJECT_ID:
        raise GEEAuthenticationError(
            "GEE_PROJECT_ID is not set.  "
            "Add it to your .env file or export it as an environment variable."
        )
    try:
        ee.Initialize(project=GEE_PROJECT_ID)
        print(f"[GEE] Authenticated with project: {GEE_PROJECT_ID}")
    except Exception as exc:
        raise GEEAuthenticationError(
            f"Failed to initialise Earth Engine: {exc}\n"
            "Run `earthengine authenticate` first."
        ) from exc


# ---------------------------------------------------------------------------
# Sentinel-2 composite
# ---------------------------------------------------------------------------

def _mask_s2_clouds(image: ee.Image) -> ee.Image:
    """Apply the Sentinel-2 SCL cloud / shadow mask."""
    scl = image.select("SCL")
    # Keep: vegetation (4), bare soil (5), water (6), unclassified (7)
    clear = (
        scl.eq(4)
        .Or(scl.eq(5))
        .Or(scl.eq(6))
        .Or(scl.eq(7))
    )
    return image.updateMask(clear)


def _add_ndvi(image: ee.Image) -> ee.Image:
    """Compute NDVI = (NIR – Red) / (NIR + Red) and add as a band."""
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return image.addBands(ndvi)


def get_sentinel2_composite(
    region: ee.Geometry,
    start_date: str,
    end_date: str,
    max_cloud_pct: float = 10,
) -> ee.Image:
    """
    Build a cloud-free, NDVI-enriched Sentinel-2 median composite.

    Parameters
    ----------
    region : ee.Geometry
        Area of interest (e.g. ``ee.Geometry.Rectangle([...])``).
    start_date : str
        Start of the date range (ISO format, e.g. ``"2024-01-01"``).
    end_date : str
        End of the date range (ISO format).
    max_cloud_pct : float, optional
        Maximum scene-level cloud cover percentage (default 10 %).

    Returns
    -------
    ee.Image
        Median composite with all S2 bands + NDVI, clipped to *region*.

    Raises
    ------
    EmptyCollectionError
        If no images remain after filtering.
    """
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud_pct))
        .map(_mask_s2_clouds)
        .map(_add_ndvi)
    )

    count = collection.size().getInfo()
    if count == 0:
        raise EmptyCollectionError(
            f"No Sentinel-2 images found for the given region "
            f"between {start_date} and {end_date} with cloud cover < {max_cloud_pct}%."
        )

    print(f"[Sentinel-2] {count} images matched — computing median composite.")
    composite = collection.median().clip(region)
    return composite


# ---------------------------------------------------------------------------
# GeoTIFF export via geemap
# ---------------------------------------------------------------------------

def export_composite_geotiff(
    composite: ee.Image,
    region: ee.Geometry,
    filename: str = "composite.tif",
    scale: int = 10,
    bands: list[str] | None = None,
) -> str:
    """
    Download the composite as a GeoTIFF to the local filesystem.

    Parameters
    ----------
    composite : ee.Image
        The EE image to export.
    region : ee.Geometry
        Bounding region for the export.
    filename : str
        Output file path (default ``"composite.tif"``).
    scale : int
        Spatial resolution in metres (default 10 m for Sentinel-2).
    bands : list[str] | None
        Band subset to export.  ``None`` exports all bands.

    Returns
    -------
    str
        Absolute path to the saved GeoTIFF.
    """
    if bands:
        composite = composite.select(bands)

    geemap.ee_export_image(
        composite,
        filename=filename,
        scale=scale,
        region=region,
        file_per_band=False,
    )
    abs_path = os.path.abspath(filename)
    print(f"[Export] GeoTIFF saved to {abs_path}")
    return abs_path


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # ── Region of Interest: Kothrud, Pune ──
    # Centre point with a 2 km buffer (buffer units are metres for EPSG:4326 points)
    LONGITUDE = 73.8077
    LATITUDE  = 18.5074
    BUFFER_M  = 2000  # 2 kilometres

    # Initial date window (3 months)
    START_DATE = "2024-01-01"
    END_DATE   = "2024-03-31"

    # Widened fallback window (full year)
    WIDE_START = "2023-01-01"
    WIDE_END   = "2024-12-31"

    authenticate_gee()

    roi = ee.Geometry.Point([LONGITUDE, LATITUDE]).buffer(BUFFER_M)

    # ── Attempt 1: narrow date range ──
    try:
        print(f"\n[Run] Date range: {START_DATE} to {END_DATE}")
        composite = get_sentinel2_composite(roi, START_DATE, END_DATE)
        date_used = (START_DATE, END_DATE)
    except EmptyCollectionError:
        # ── Attempt 2: widened date range (auto-retry) ──
        print(
            f"[Retry] No cloud-free images in {START_DATE}-{END_DATE}. "
            f"Widening to {WIDE_START}-{WIDE_END} and retrying..."
        )
        print(f"\n[Run] Date range: {WIDE_START} to {WIDE_END}")
        composite = get_sentinel2_composite(roi, WIDE_START, WIDE_END)
        date_used = (WIDE_START, WIDE_END)

    # ── Summary ──
    print(f"\n{'='*50}")
    print(f"Region        : Kothrud, Pune")
    print(f"Centre        : {LATITUDE} N, {LONGITUDE} E")
    print(f"Buffer        : {BUFFER_M / 1000:.0f} km")
    print(f"Date range    : {date_used[0]} to {date_used[1]}")
    print(f"{'='*50}")

    export_composite_geotiff(
        composite,
        region=roi,
        filename="kothrud_pune_composite.tif",
        bands=["B4", "B3", "B2", "NDVI"],
    )
