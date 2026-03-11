import rasterio
import rasterio.mask
import numpy as np
import geopandas as gpd
import requests
import pandas as pd
from shapely.geometry import shape, Point
from pyproj import Transformer


STAC_URL = "https://earth-search.aws.element84.com/v0/search"


def fetch_sentinel_data(polygon_geojson):
    """
    Query Sentinel-2 STAC API and return asset URLs.
    """

    query = {
        "collections": ["sentinel-s2-l2a-cogs"],
        "intersects": polygon_geojson["features"][0]["geometry"],
        "datetime": "2025-01-01T00:00:00Z/2025-09-25T23:59:59Z",
        "limit": 1,
        "query": {"eo:cloud_cover": {"lt": 80}},
        "sort": [{"field": "datetime", "direction": "desc"}]
    }

    resp = requests.post(STAC_URL, json=query)

    if resp.status_code != 200:
        raise Exception(f"STAC API error {resp.status_code}: {resp.text}")

    items = resp.json().get("features", [])

    if not items:
        raise Exception("No Sentinel-2 imagery found")

    assets = items[0]["assets"]

    print("Available assets:", list(assets.keys()))

    B04_URL = assets["B04"]["href"]
    B08_URL = assets["B08"]["href"]

    print("Red band:", B04_URL)
    print("NIR band:", B08_URL)

    return B04_URL, B08_URL


def download_bands(red_url, nir_url):
    """
    Download Sentinel-2 bands.
    """

    def download(url, filename):
        r = requests.get(url, stream=True)
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded {filename}")

    download(red_url, "B04.tif")
    download(nir_url, "B08.tif")

    return "B04.tif", "B08.tif"


def clip_raster(band_file, polygon_geojson):
    """
    Clip raster using polygon boundary.
    """

    with rasterio.open(band_file) as src:

        geom = shape(polygon_geojson["features"][0]["geometry"])
        gdf = gpd.GeoDataFrame(geometry=[geom], crs="EPSG:4326")

        gdf = gdf.to_crs(src.crs)

        clipped, transform = rasterio.mask.mask(src, gdf.geometry, crop=True)

        meta = src.meta.copy()

        meta.update({
            "driver": "GTiff",
            "height": clipped.shape[1],
            "width": clipped.shape[2],
            "transform": transform
        })

    return clipped[0], meta


def calculate_ndvi(red, nir):
    """
    Calculate NDVI index.
    """

    ndvi = (nir.astype(float) - red.astype(float)) / (nir + red + 1e-6)

    print("NDVI Stats:")
    print("Mean:", float(np.nanmean(ndvi)))
    print("Min :", float(np.nanmin(ndvi)))
    print("Max :", float(np.nanmax(ndvi)))

    return ndvi


def save_output(ndvi, red_meta):
    """
    Save NDVI raster.
    """

    ndvi_meta = red_meta.copy()

    ndvi_meta.update(dtype=rasterio.float32, count=1)

    with rasterio.open("ndvi.tif", "w", **ndvi_meta) as dst:
        dst.write(ndvi.astype(np.float32), 1)

    print("NDVI raster saved as ndvi.tif")

    return ndvi_meta


def sample_ndvi(ndvi_meta, polygon_geojson, step=1):

    geom = shape(polygon_geojson["features"][0]["geometry"])

    gdf_poly = gpd.GeoDataFrame(
        geometry=[geom],
        crs="EPSG:4326"
    ).to_crs(ndvi_meta["crs"])

    minx, miny, maxx, maxy = gdf_poly.total_bounds

    xs = np.arange(minx, maxx, step)
    ys = np.arange(miny, maxy, step)

    samples = []

    with rasterio.open("ndvi.tif") as src:

        for x in xs:
            for y in ys:

                pt = Point(x, y)

                if gdf_poly.contains(pt).any():

                    for val in src.sample([(x, y)]):
                        samples.append((x, y, val[0]))

    df = pd.DataFrame(samples, columns=["x", "y", "ndvi"])

    raster_crs = ndvi_meta["crs"]

    transformer = Transformer.from_crs(
        raster_crs,
        "EPSG:4326",
        always_xy=True
    )

    df["lon"], df["lat"] = transformer.transform(
        df["x"].values,
        df["y"].values
    )

    df[["lon", "lat", "ndvi"]].to_csv("ndvi_points.csv", index=False)

    print("NDVI samples saved to ndvi_points.csv")

    return df