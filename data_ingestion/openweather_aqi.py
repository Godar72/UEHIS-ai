"""
data_ingestion/openweather_aqi.py
---------------------------------
Fetches air quality data from the OpenWeather Air Pollution API for
a grid of block centroids.  Returns PM2.5 concentration (ug/m3) as the
continuous AQI proxy, along with the 1-5 AQI index and PM10.

Responses are cached locally to avoid re-querying the same coordinates
(OpenWeather free tier has rate limits).
"""

import os
import json
import hashlib
import time

import requests
import numpy as np
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache", "aqi")
API_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

# Rate-limit delay between API calls (seconds)
_RATE_DELAY = 0.15  # ~6-7 requests/sec, well within free tier limits


class AQIFetchError(Exception):
    """Raised when the OpenWeather API request fails."""
    pass


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_key(lat: float, lon: float) -> str:
    """Generate a deterministic cache key from rounded coordinates."""
    # Round to 4 decimal places (~11m precision) to bucket nearby centroids
    key_str = f"{lat:.4f},{lon:.4f}"
    return hashlib.md5(key_str.encode()).hexdigest()


def _read_cache(lat: float, lon: float) -> dict | None:
    """Read cached API response for a coordinate, or None if not cached."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{_cache_key(lat, lon)}.json")
    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)
    return None


def _write_cache(lat: float, lon: float, data: dict) -> None:
    """Write API response to cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{_cache_key(lat, lon)}.json")
    with open(cache_file, "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# API query
# ---------------------------------------------------------------------------

def _fetch_aqi_single(lat: float, lon: float) -> dict:
    """
    Query OpenWeather Air Pollution API for a single coordinate.

    Returns
    -------
    dict
        Keys: ``aqi_index`` (1-5), ``pm2_5``, ``pm10`` (ug/m3).

    Raises
    ------
    AQIFetchError
        If the API request fails or returns unexpected data.
    """
    # Check cache first
    cached = _read_cache(lat, lon)
    if cached is not None:
        return cached

    if not OPENWEATHER_API_KEY:
        raise AQIFetchError(
            "OPENWEATHER_API_KEY is not set. "
            "Add it to your .env file."
        )

    params = {
        "lat": round(lat, 4),
        "lon": round(lon, 4),
        "appid": OPENWEATHER_API_KEY,
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise AQIFetchError(f"API request failed for ({lat}, {lon}): {exc}") from exc

    data = resp.json()

    if "list" not in data or len(data["list"]) == 0:
        raise AQIFetchError(f"Empty response for ({lat}, {lon}): {data}")

    entry = data["list"][0]
    result = {
        "aqi_index": entry["main"]["aqi"],  # 1-5 scale
        "pm2_5": entry["components"].get("pm2_5", np.nan),
        "pm10": entry["components"].get("pm10", np.nan),
    }

    # Cache the result
    _write_cache(lat, lon, result)

    return result


# ---------------------------------------------------------------------------
# Batch query for block grid
# ---------------------------------------------------------------------------

def fetch_aqi_for_blocks(
    block_grid: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """
    Fetch AQI data for the centroid of each block in a grid.

    Parameters
    ----------
    block_grid : gpd.GeoDataFrame
        Grid of block polygons (must have a CRS set).

    Returns
    -------
    pd.DataFrame
        Columns: ``aqi_index``, ``pm2_5``, ``pm10``.
        Index aligned with *block_grid*.
        Failed queries have ``NaN`` values.
    """
    results = []
    n_cached = 0
    n_fetched = 0
    n_failed = 0

    # Ensure we work in EPSG:4326 for lat/lon
    if block_grid.crs and block_grid.crs.to_epsg() != 4326:
        centroids = block_grid.to_crs(epsg=4326).geometry.centroid
    else:
        centroids = block_grid.geometry.centroid

    total = len(centroids)
    for i, centroid in enumerate(centroids):
        lat, lon = centroid.y, centroid.x
        try:
            # Check if this is a cache hit (no delay needed)
            cached = _read_cache(lat, lon)
            if cached is not None:
                results.append(cached)
                n_cached += 1
            else:
                result = _fetch_aqi_single(lat, lon)
                results.append(result)
                n_fetched += 1
                # Rate limit only for actual API calls
                time.sleep(_RATE_DELAY)

            # Progress indicator every 50 blocks
            if (i + 1) % 50 == 0 or (i + 1) == total:
                print(f"  [AQI] Progress: {i+1}/{total} blocks "
                      f"(cached: {n_cached}, fetched: {n_fetched}, failed: {n_failed})")

        except AQIFetchError as exc:
            results.append({
                "aqi_index": np.nan,
                "pm2_5": np.nan,
                "pm10": np.nan,
            })
            n_failed += 1
            if n_failed <= 3:
                print(f"  [AQI] WARNING: {exc}")

    print(f"[AQI] Done: {n_cached} cached, {n_fetched} fetched, {n_failed} failed")

    return pd.DataFrame(results, index=block_grid.index)


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from shapely.geometry import box as shapely_box
    import math

    # Same Kothrud ROI as other modules
    LONGITUDE = 73.8077
    LATITUDE = 18.5074
    BUFFER_DEG = 2000 / 111320  # ~2km in degrees

    west = LONGITUDE - BUFFER_DEG
    east = LONGITUDE + BUFFER_DEG
    south = LATITUDE - BUFFER_DEG
    north = LATITUDE + BUFFER_DEG

    # Create a small test grid (just 4 blocks to verify API)
    test_cells = []
    mid_lat = (south + north) / 2
    mid_lon = (west + east) / 2
    for r, lat in enumerate([south, mid_lat]):
        for c, lon in enumerate([west, mid_lon]):
            test_cells.append({
                "geometry": shapely_box(lon, lat, lon + BUFFER_DEG, lat + BUFFER_DEG),
                "block_id": f"TEST_R{r}_C{c}",
            })

    test_grid = gpd.GeoDataFrame(test_cells, crs="EPSG:4326")
    print(f"Testing with {len(test_grid)} blocks...")

    aqi_df = fetch_aqi_for_blocks(test_grid)
    print("\nResults:")
    print(aqi_df.to_string())
    print(f"\nPM2.5 range: {aqi_df['pm2_5'].min():.1f} - {aqi_df['pm2_5'].max():.1f} ug/m3")
