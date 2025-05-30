import ee
import pandas as pd
import json

ee.Initialize(project='gen-lang-client-0972336843')

# --- load tile CSV ---
csv_path = './exports/tile_feature_export.csv'
df = pd.read_csv(csv_path)

# --- convert .geo column to ee.Geometry ---
def row_to_feature(row):
    geom = ee.Geometry(json.loads(row['.geo']))
    return ee.Feature(geom, {
        'tile_id': row['tile_id'],
        'elevation': row['elevation'],
        'slope': row['slope']
    })

features = [row_to_feature(row) for _, row in df.iterrows()]
fc = ee.FeatureCollection(features)

# --- load water point data ---
wpdx = ee.FeatureCollection("WPDx/water_points")

# --- calculate distance to water for each tile ---
def add_distance(tile):
    dist = wpdx.distance(ee.ErrorMargin(1)).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=tile.geometry(),
        scale=30
    ).get('distance')
    return tile.set('distance_to_water', dist)

labeled_fc = fc.map(add_distance)

# --- export updated features as CSV ---
task = ee.batch.Export.table.toDrive(
    collection=labeled_fc,
    description='new_tile_features',
    fileFormat='CSV',
    folder='EarthEngineExports'
)

task.start()
print("export started!")
