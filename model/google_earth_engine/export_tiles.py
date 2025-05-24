import ee

ee.Initialize(project='gen-lang-client-0972336843')

# region of interest (area around west kenya)
roi = ee.Geometry.Rectangle([33.9, -1.5, 35.3, 0.8])
dx, dy = 0.01, 0.01  # around 1 km

# get sentinel-2 data
collection = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterBounds(roi) \
    .filterDate('2022-01-01', '2022-03-31') \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
composite = collection.median().select(['B4', 'B3', 'B2'])

# elevation data
elevation = ee.Image('USGS/SRTMGL1_003')
slope = ee.Terrain.slope(elevation)

# make tiles, export images and compute features
features = []
tile_count = 0
x = 33.9
while x < 35.3:
    y = -1.5
    while y < 0.8:
        tile_geom = ee.Geometry.Rectangle([x, y, x + dx, y + dy])
        tile_id = f"tile_{round(x, 3)}_{round(y, 3)}"

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

        tile_count += 1
        y += dy
    x += dx

print(f"started export tasks for {tile_count} image tiles.")

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
