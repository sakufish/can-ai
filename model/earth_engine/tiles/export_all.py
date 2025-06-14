import ee

ee.Initialize(project='gen-lang-client-0972336843')

# --- parameters ---
ROI_BOUNDS = [31.9, 0.2, 34.5, 2.5]  # parts of kenya & uganda
dx, dy = 0.01, 0.01                 
NUM_TILES = 3000   # gee queue quota  

roi = ee.Geometry.Rectangle(ROI_BOUNDS)

collection = (
    ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
      .filterBounds(roi)
      .filterDate('2022-01-01', '2022-03-31')
      .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
)
composite = collection.median().select(['B4', 'B3', 'B2'])

elevation = ee.Image('USGS/SRTMGL1_003')
slope = ee.Terrain.slope(elevation)

# --- additional features ---
landcover = ee.ImageCollection("ESA/WorldCover/v100").first().select('Map')
ndvi = collection.median().normalizedDifference(['B8', 'B4']).rename('NDVI')
viirs = ee.ImageCollection('NOAA/VIIRS/DNB/MONTHLY_V1/VCMSLCFG') \
    .filterDate('2022-01-01', '2022-01-31') \
    .median().select('avg_rad')
water_occurrence = ee.Image('JRC/GSW1_3/GlobalSurfaceWater').select('occurrence')
permanent_water = water_occurrence.gt(80)
water_distance = permanent_water.Not().fastDistanceTransform(30).sqrt().multiply(30).rename('distance_to_water')

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

# --- assign tile_id to match image export ---
sampled_list = sampled_fc_raw.toList(NUM_TILES)
sampled_fc = ee.FeatureCollection(ee.List.sequence(0, NUM_TILES - 1).map(
    lambda i: ee.Feature(sampled_list.get(i)).set('tile_id', ee.String('tile_').cat(ee.Number(i).toInt().format('%d')))
))

# --- load water point dataset ---
water_points = ee.FeatureCollection('users/cadenchen/kenya_expanded')

# --- safe‐aggregate helpers ---
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

def safe_aggregate_min(fc, prop, default):
    return ee.Number(
        ee.Algorithms.If(fc.size().gt(0), fc.aggregate_min(prop), default)
    )

# --- compute attributes (with distance‐weighted sources) ---
def add_attrs(tile):
    tile_geom = tile.geometry()
    buffer_geom = tile_geom.buffer(5000)  # 5 km buffer

    # 1) choose sources inside tile. if none, use buffer
    in_tile = water_points.filterBounds(tile_geom).filter(ee.Filter.eq('status_id', 'Yes'))
    in_buffer = water_points.filterBounds(buffer_geom).filter(ee.Filter.eq('status_id', 'Yes'))
    functional = ee.FeatureCollection(
        ee.Algorithms.If(in_tile.size().gt(0), in_tile, in_buffer)
    )

    # 2) raw counts & simple stats
    num_sources = functional.size()
    pressure = safe_aggregate_mean(functional, 'pressure_score', 0)
    pop = safe_aggregate_mean(functional, 'water_point_population', 0)

    # 3) normalize & cap
    norm_pressure = ee.Number(pressure).divide(1.5).min(2.0)
    norm_pop = ee.Number(pop).divide(1000).min(5.0) 

    # 4) distance‐weighted source score
    var_centroid = tile_geom.centroid()
    with_dist = functional.map(lambda f:
        f.set('dist', f.geometry().distance(var_centroid))
    )
    max_dist = 10000  # 10 km
    weighted = with_dist.map(lambda f:
        f.set('w', ee.Number(1).subtract(ee.Number(f.get('dist')).divide(max_dist)).max(0))
    )
    sum_w = ee.Number(weighted.aggregate_sum('w')).min(10)
    weighted_score = sum_w.divide(8).multiply(0.4)

    # 5) category bonus
    category = safe_aggregate_mode(functional, 'water_source_category', 'Unknown')
    has_bonus = ee.String(category).match('Well|Spring|Piped').size().gt(0)
    category_bonus = ee.Number(ee.Algorithms.If(has_bonus, 0.1, -0.1))

    # 6) final score
    var_score = (
        norm_pressure.multiply(0.3)
        .add(norm_pop.multiply(0.2))
        .add(weighted_score)
        .add(category_bonus)
    )

    # 7) elevation & slope 
    elev = elevation.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=tile_geom,
        scale=30
    ).get('elevation')

    slp = slope.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=tile_geom,
        scale=30
    ).get('slope')

    # 8) land cover
    lc = landcover.reduceRegion(
        reducer=ee.Reducer.mode(),
        geometry=tile_geom,
        scale=10,
        maxPixels=1e8
    ).get('Map')

    # 9) ndvi (vegetation health)
    mean_ndvi = ndvi.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=tile_geom,
        scale=10,
        maxPixels=1e8
    ).get('NDVI')

    # 10) nighttime lights
    night = viirs.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=tile_geom,
        scale=500,
        maxPixels=1e8
    ).get('avg_rad')

    # 11) waterbody distance
    raw_dist = water_distance.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=tile_geom,
        scale=30,
        maxPixels=1e8
    ).get('distance_to_water')
    capped_dist = ee.Number(raw_dist).min(2000)

    return tile.set({
        'score': var_score,
        'pressure_score': pressure,
        'water_point_population': pop,
        'num_sources': num_sources,
        'distance_weighted_score': sum_w,
        'norm_distance_weighted': weighted_score,
        'water_source_category': category,
        'category_bonus': category_bonus,
        'elevation': elev,
        'slope': slp,
        'land_cover_class': lc,
        'mean_ndvi': mean_ndvi,
        'nighttime_light': night,
        'mean_distance_to_water': capped_dist
    })

feature_collection = sampled_fc.map(add_attrs)

# --- export CSV ---
feature_task = ee.batch.Export.table.toDrive(
    collection=feature_collection,
    description='tile_feature_export',
    fileFormat='CSV',
    folder='EarthEngineExports'
)
feature_task.start()
print("feature csv export task started.")

# --- export image tiles ---
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
    if (i + 1) % 100 == 0 or i == NUM_TILES - 1:
        print(f"started export task {i + 1} / {NUM_TILES}")

print(f"started export tasks for {NUM_TILES} image tiles.")