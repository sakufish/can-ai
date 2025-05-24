import ee

ee.Initialize(project='gen-lang-client-0972336843')

# region of interest centered on armenia
roi = ee.Geometry.Rectangle([43.5, 38.5, 47.5, 41.5])  # smaller box

dx, dy = 0.01, 0.01  # around 1 km per tile

# get sentinel-2 data
collection = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterBounds(roi) \
    .filterDate('2022-01-01', '2022-03-31') \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
composite = collection.median().select(['B4', 'B3', 'B2'])

# elevation data
elevation = ee.Image('USGS/SRTMGL1_003')
slope = ee.Terrain.slope(elevation)

# generate tile grid
tiles = []
x = 43.5
while x < 47.5:
    y = 38.5
    while y < 41.5:
        tile = ee.Geometry.Rectangle([x, y, x + dx, y + dy])
        tiles.append(tile)
        y += dy
    x += dx

# randomly sample 4000 tiles
sampled_tiles = ee.List(tiles).slice(0, 4000).getInfo()

# make tiles, export images and compute features
features = []
for i, tile_geom_coords in enumerate(sampled_tiles):
    tile_geom = ee.Geometry.Rectangle(tile_geom_coords)
    tile_id = f"tile_{i}"           

    # get per-tile features
    elev = elevation.reduceRegion(reducer=ee.Reducer.mean(), geometry=tile_geom, scale=30).get('elevation')
    slp = slope.reduceRegion(reducer=ee.Reducer.mean(), geometry=tile_geom, scale=30).get('slope')

    feat = ee.Feature(tile_geom, {
        'tile_id': tile_id,
        'elevation': elev,
        'slope': slp
    })
    features.append(feat)

    # export image tile to drive
    export_task = ee.batch.Export.image.toDrive(
        image=composite.clip(tile_geom),
        description=f"sentinel2_{tile_id}",
        folder="EarthEngineExports",
        region=tile_geom,
        scale=10,
        maxPixels=1e8 
    )
    export_task.start()

print("started export tasks for image tiles.")

# export feature table as csv
feature_collection = ee.FeatureCollection(features)
feature_task = ee.batch.Export.table.toDrive(
    collection=feature_collection,
    description='tile_feature_export',
    fileFormat='CSV',
    folder='EarthEngineExports'
)
feature_task.start()
print("feature csv export task started.")
