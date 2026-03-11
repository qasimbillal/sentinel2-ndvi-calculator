from src.ndvi_calculator import *

polygon_geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [72.68842039311673,32.713740339142376],
                    [72.68835995099107,32.71346741759562],
                    [72.68844255523007,32.71339283019584],
                    [72.68851911525667,32.71330129102823],
                    [72.68872260374897,32.713189409695914],
                    [72.68876491323752,32.71327586346452],
                    [72.68885356168886,32.71334197511413],
                    [72.68881528167654,32.71339113502643],
                    [72.68887169432597,32.71346572242848],
                    [72.68883139957555,32.713545395266095],
                    [72.68877498692413,32.713670837461535],
                    [72.68871454479847,32.71365388582396],
                    [72.68865813214711,32.71376068108752],
                    [72.68842039311673,32.713740339142376]
                ]]
            }
        }
    ]
}


red_url, nir_url = fetch_sentinel_data(polygon_geojson)

red_file, nir_file = download_bands(red_url, nir_url)

red, red_meta = clip_raster(red_file, polygon_geojson)
nir, nir_meta = clip_raster(nir_file, polygon_geojson)

ndvi = calculate_ndvi(red, nir)

ndvi_meta = save_output(ndvi, red_meta)

samples = sample_ndvi(ndvi_meta, polygon_geojson)