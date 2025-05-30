import ee

ee.Initialize(project='gen-lang-client-0972336843')

# --- parameters ---
ROI_BOUNDS = [31.9, 0.2, 34.5, 2.5]  # parts of kenya & uganda
dx, dy = 0.01, 0.01                 
NUM_TILES = 1000   # reduced to 1k for test run

roi = ee.Geometry.Rectangle(ROI_BOUNDS)

# --- land cover image ---
landcover = ee.ImageCollection("ESA/WorldCover/v100").first().select('Map')

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

# --- assign tile id  ---
sampled_list = sampled_fc_raw.toList(NUM_TILES)
sampled_fc = ee.FeatureCollection(ee.List.sequence(0, NUM_TILES - 1).map(
    lambda i: ee.Feature(sampled_list.get(i)).set('tile_id', ee.String('tile_').cat(ee.Number(i).format()))
))

# --- land cover mode ---
def add_landcover(tile):
    geom = tile.geometry()
    lc = landcover.reduceRegion(
        reducer=ee.Reducer.mode(),
        geometry=geom,
        scale=10,
        maxPixels=1e8
    ).get('Map')
    return tile.set({'land_cover_class': lc})

feature_collection = sampled_fc.map(add_landcover)

# --- export CSV ---
feature_task = ee.batch.Export.table.toDrive(
    collection=feature_collection,
    description='landcover_export',
    fileFormat='CSV',
    folder='EarthEngineExports'
)
feature_task.start()
print("land cover CSV export task started.")
