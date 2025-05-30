import ee

ee.Initialize(project='gen-lang-client-0972336843')

# --- parameters ---
ROI_BOUNDS = [33.9, -1.5, 35.3, 0.8]  # western kenya  
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

# --- load water point dataset from google earth engine ---
water_points = ee.FeatureCollection('users/cadenchen/wpdx_cleaned4')

# --- safe aggregate helpers ---
def safe_aggregate_mean(fc, prop, default=0):
    return ee.Number(
        ee.Algorithms.If(fc.size().gt(0), fc.aggregate_mean(prop), default)
    )

def safe_aggregate_mode(fc, prop, default='Unknown'):
    hist = ee.Dictionary(
        ee.Algorithms.If(fc.size().gt(0), fc.aggregate_histogram(prop), ee.Dictionary({}))
    )
    keys = hist.keys()
    values = hist.values()
    max_index = values.indexOf(values.reduce(ee.Reducer.max()))
    mode = ee.Algorithms.If(
        keys.size().gt(0),
        keys.get(max_index),
        default
    )
    return ee.String(mode)

# --- compute attributes ---
def add_attrs(tile):
    tile_geom = tile.geometry()
    functional = water_points \
        .filterBounds(tile_geom) \
        .filter(ee.Filter.eq('status_id', 'Yes'))

    num_sources = functional.size()
    pressure = safe_aggregate_mean(functional, 'pressure_score', 0)
    pop = safe_aggregate_mean(functional, 'water_point_population', 0)
    d1 = safe_aggregate_mean(functional, 'distance_to_primary_road', 50000)
    d2 = safe_aggregate_mean(functional, 'distance_to_secondary_road', 20000)
    d3 = safe_aggregate_mean(functional, 'distance_to_tertiary_road', 10000)
    d_city = safe_aggregate_mean(functional, 'distance_to_city', 25000)
    d_town = safe_aggregate_mean(functional, 'distance_to_town', 10000)
    local_pop = safe_aggregate_mean(functional, 'local_population_1km', 0)
    urban_majority = safe_aggregate_mode(functional, 'is_urban', 'false')
    category = safe_aggregate_mode(functional, 'water_source_category', 'Unknown')

    # normalize values
    norm_pressure = ee.Number(pressure).divide(1.5)
    norm_pop = ee.Number(pop).divide(1000)
    norm_d1 = ee.Number(d1).divide(50000)
    norm_d2 = ee.Number(d2).divide(20000)
    norm_d3 = ee.Number(d3).divide(10000)

    # category bonus: use .match().size().gt(0)
    category_str = ee.String(category)
    is_well   = category_str.match('Well').size().gt(0)
    is_spring = category_str.match('Spring').size().gt(0)
    is_piped  = category_str.match('Piped').size().gt(0)
    has_bonus = is_well.Or(is_spring).Or(is_piped)
    category_bonus = ee.Algorithms.If(
        has_bonus,
        0.1,
        -0.1
    )

    # functional water source weighting (capped at 8)
    functional_weight = ee.Number(num_sources).min(8).multiply(0.05)

    # compute final score
    score = norm_pressure.multiply(0.3) \
        .add(norm_pop.multiply(0.2)) \
        .add(functional_weight) \
        .subtract(norm_d1.multiply(0.2)) \
        .subtract(norm_d2.multiply(0.05)) \
        .subtract(norm_d3.multiply(0.05)) \
        .add(ee.Number(category_bonus))

    elev = elevation.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=tile_geom, scale=30
    ).get('elevation')
    slp = slope.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=tile_geom, scale=30
    ).get('slope')

    return tile.set({
        'score': score,
        'pressure_score': pressure,
        'water_point_population': pop,
        'distance_to_primary_road': d1,
        'distance_to_secondary_road': d2,
        'distance_to_tertiary_road': d3,
        'distance_to_city': d_city,
        'distance_to_town': d_town,
        'local_population_1km': local_pop,
        'is_urban': urban_majority,
        'water_source_category': category,
        'num_sources': num_sources,
        'elevation': elev,
        'slope': slp
    })

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