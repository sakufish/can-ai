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

# create tiles
tiles = []
x = 33.9
while x < 35.3:
    y = -1.5
    while y < 0.8:
        tile = ee.Geometry.Rectangle([x, y, x + dx, y + dy])
        tiles.append(tile)
        y += dy
    x += dx

# test export to google drive
for i, region in enumerate(tiles[:10]):
    task = ee.batch.Export.image.toDrive(
        image=composite.clip(region),
        description=f"Sentinel2_Tile_{i}",
        folder="EarthEngineExports",
        region=region,
        scale=10,
        maxPixels=1e8
    )
    task.start()
    print(f"started export task for tile {i}")
