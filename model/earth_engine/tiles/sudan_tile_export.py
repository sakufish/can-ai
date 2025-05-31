import ee

ee.Initialize(project='gen-lang-client-0972336843')

# --- Kampala  ---
ROI_BOUNDS = [32.6, 0.3, 32.85, 0.7]
dx, dy = 0.01, 0.01
NUM_TILES = 1000

roi = ee.Geometry.Rectangle(ROI_BOUNDS)

# --- satellite Layers ---
collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterBounds(roi) \
    .filterDate('2022-01-01', '2022-03-31') \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
composite = collection.median().select(['B4', 'B3', 'B2'])
ndvi = collection.median().normalizedDifference(['B8', 'B4']).rename('NDVI')

elevation = ee.Image('USGS/SRTMGL1_003')
slope = ee.Terrain.slope(elevation)
landcover = ee.ImageCollection("ESA/WorldCover/v100").first().select('Map')
viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG') \
    .filterDate('2022-01-01', '2022-01-31') \
    .median().select('avg_rad')
water_occurrence = ee.Image('JRC/GSW1_3/GlobalSurfaceWater').select('occurrence')
permanent_water = water_occurrence.gt(80)
water_distance = permanent_water.Not().fastDistanceTransform(30).sqrt().multiply(30).rename('distance_to_water')

# --- this does it in a box for better visiualization ---
def make_tile(x, y):
    x = ee.Number(x)
    y = ee.Number(y)
    geom = ee.Geometry.Rectangle([x, y, x.add(dx), y.add(dy)])
    return ee.Feature(geom)

xs = ee.List.sequence(ROI_BOUNDS[0], ROI_BOUNDS[2] - 1e-9, dx)
ys = ee.List.sequence(ROI_BOUNDS[1], ROI_BOUNDS[3] - 1e-9, dy)
tiles = xs.map(lambda x: ys.map(lambda y: make_tile(x, y))).flatten()
tile_fc = ee.FeatureCollection(tiles).limit(NUM_TILES)

# --- assign correct tile id ---
sampled_fc = ee.FeatureCollection(ee.List.sequence(0, NUM_TILES - 1).map(
    lambda i: ee.Feature(tile_fc.toList(NUM_TILES).get(i)).set(
        'tile_id', ee.String('tile_').cat(ee.Number(i).toInt().format()))
))

# --- add the features only ---
def add_attrs(tile):
    geom = tile.geometry()

    elev = elevation.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=30).get('elevation')
    slp = slope.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=30).get('slope')
    lc = landcover.reduceRegion(reducer=ee.Reducer.mode(), geometry=geom, scale=10, maxPixels=100000000).get('Map')
    nd = ndvi.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=10, maxPixels=100000000).get('NDVI')
    night = viirs.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=500, maxPixels=100000000).get('avg_rad')
    raw_dist = water_distance.reduceRegion(reducer=ee.Reducer.mean(), geometry=geom, scale=30, maxPixels=100000000).get('distance_to_water')
    capped_dist = ee.Number(raw_dist).min(2000)

    return tile.set({
        'elevation': elev,
        'slope': slp,
        'land_cover_class': lc,
        'mean_ndvi': nd,
        'nighttime_light': night,
        'mean_distance_to_water': capped_dist
    })

feature_collection = sampled_fc.map(add_attrs)

# --- export CSV ---
ee.batch.Export.table.toDrive(
    collection=feature_collection,
    description='sudan_tile_features',
    folder='EarthEngineExports',
    fileFormat='CSV'
).start()

print("feature CSV export started.")

# --- export sentinel 2 image tiles ---
sampled_list = sampled_fc.toList(NUM_TILES)
for i in range(NUM_TILES):
    tile = ee.Feature(sampled_list.get(i))
    tile_geom = tile.geometry()
    export_task = ee.batch.Export.image.toDrive(
        image=composite.clip(tile_geom),
        description=f"tile_{i}",
        folder="EarthEngineExports",
        fileNamePrefix=f"tile_{i}",
        region=tile_geom,
        scale=10,
        maxPixels=100000000
    )
    export_task.start()
    if (i + 1) % 100 == 0 or i == NUM_TILES - 1:
        print(f"started export task {i + 1} / {NUM_TILES}")

print(f"started export tasks for {NUM_TILES} image tiles.")
