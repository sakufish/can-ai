import ee

ee.Initialize(project='gen-lang-client-0972336843')

# --- parameters ---
ROI_BOUNDS = [43.5, 38.5, 47.5, 41.5]
dx, dy = 0.01, 0.01  # tile size
NUM_TILES = 3000     # set to 3000 to fit within EE export quota

roi = ee.Geometry.Rectangle(ROI_BOUNDS)

collection = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
    .filterBounds(roi) \
    .filterDate('2022-01-01', '2022-03-31') \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
composite = collection.median().select(['B4', 'B3', 'B2'])

elevation = ee.Image('USGS/SRTMGL1_003')
slope = ee.Terrain.slope(elevation)

# --- generate tile grids ---
def make_tile(x, y):
    x = ee.Number(x)
    y = ee.Number(y)
    geom = ee.Geometry.Rectangle([x, y, x.add(dx), y.add(dy)])
    tile_id = ee.String('tile_').cat(x.format('%.3f')).cat('_').cat(y.format('%.3f'))
    return ee.Feature(geom, {'tile_id': tile_id})

xs = ee.List.sequence(ROI_BOUNDS[0], ROI_BOUNDS[2] - dx, dx)
ys = ee.List.sequence(ROI_BOUNDS[1], ROI_BOUNDS[3] - dy, dy)
tiles_nested = xs.map(lambda x: ys.map(lambda y: make_tile(x, y)))
tiles_flat = tiles_nested.flatten()
tile_fc = ee.FeatureCollection(tiles_flat)
sampled_fc = tile_fc.randomColumn().sort('random').limit(NUM_TILES)

# --- compute attributes ---
def add_attrs(tile):
    tile_geom = tile.geometry()
    elev = elevation.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=tile_geom, scale=30
    ).get('elevation')
    slp = slope.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=tile_geom, scale=30
    ).get('slope')
    return tile.set({'elevation': elev, 'slope': slp})

feature_collection = sampled_fc.map(add_attrs)

# --- export csv ---
feature_task = ee.batch.Export.table.toDrive(
    collection=feature_collection,
    description='tile_feature_export',
    fileFormat='CSV',
    folder='EarthEngineExports'
)
feature_task.start()
print("feature csv export task started.")

# --- export all the images (capped at 3000) ---
sampled_list = sampled_fc.toList(NUM_TILES)
for i in range(NUM_TILES):
    tile = ee.Feature(sampled_list.get(i))
    tile_geom = tile.geometry()
    export_task = ee.batch.Export.image.toDrive(
        image=composite.clip(tile_geom),
        description=f"sentinel2_tile_{i}",
        folder="EarthEngineExports",
        region=tile_geom,
        scale=10,
        maxPixels=1e8
    )
    export_task.start()
    if (i+1) % 100 == 0 or i == NUM_TILES-1:
        print(f"started export task {i+1} / {NUM_TILES}")

print(f"started export tasks for {NUM_TILES} image tiles.")