import ee

ee.Initialize(project='gen-lang-client-0972336843')

# --- parameters ---
ROI_BOUNDS = [31.9, 0.2, 34.5, 2.5]
dx, dy = 0.01, 0.01
NUM_TILES = 1000

roi = ee.Geometry.Rectangle(ROI_BOUNDS)

# --- viirs nighttime lights (january 2022 average radiance) ---
viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG') \
    .filterDate('2022-01-01', '2022-01-31') \
    .median() \
    .select('avg_rad')

# --- generate tile grids ---
def make_tile(x, y):
    x = ee.Number(x)
    y = ee.Number(y)
    geom = ee.Geometry.Rectangle([x, y, x.add(dx), y.add(dy)])
    return ee.Feature(geom)

xs = ee.List.sequence(ROI_BOUNDS[0], ROI_BOUNDS[2] - dx, dx)
ys = ee.List.sequence(ROI_BOUNDS[1], ROI_BOUNDS[3] - dy, dy)
tiles_nested = xs.map(lambda x: ys.map(lambda y: make_tile(x, y)))
tiles_flat = tiles_nested.flatten()
tile_fc = ee.FeatureCollection(tiles_flat)
sampled_fc_raw = tile_fc.randomColumn().sort('random').limit(NUM_TILES)

# --- assign tile id ---
sampled_list = sampled_fc_raw.toList(NUM_TILES)
sampled_fc = ee.FeatureCollection(ee.List.sequence(0, NUM_TILES - 1).map(
    lambda i: ee.Feature(sampled_list.get(i)).set('tile_id', ee.String('tile_').cat(ee.Number(i).format()))
))

# --- mean radiance per tile ---
def add_nightlight(tile):
    geom = tile.geometry()
    night = viirs.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=500,
        maxPixels=1e8
    ).get('avg_rad')
    return tile.set({'nighttime_light': night})

feature_collection = sampled_fc.map(add_nightlight)

# --- export CSV ---
task = ee.batch.Export.table.toDrive(
    collection=feature_collection,
    description='nightlight_export',
    fileFormat='CSV',
    folder='EarthEngineExports'
)
task.start()
print("nighttime light CSV export task started.")
