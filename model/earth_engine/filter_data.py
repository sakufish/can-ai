import pandas as pd

# --- load and filter valid entries ---
df = pd.read_csv('../data/raw.csv', encoding='utf-8', low_memory=False)
df = df.dropna(subset=['latitude', 'longitude'])

df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
df = df.dropna(subset=['latitude', 'longitude'])

# --- only keep entries within western kenya bounds ---
df = df[
    (df['latitude'] > -1.5) & (df['latitude'] < 0.8) &
    (df['longitude'] > 33.9) & (df['longitude'] < 35.3)
]

# --- select relevant columns ---
columns_to_keep = [
    'latitude',
    'longitude',
    '#status_id',
    '#water_source_clean',
    '#water_source_category',
    '#water_tech_category',
    '#distance_to_primary_road',
    '#distance_to_secondary_road',
    '#distance_to_tertiary_road',
    '#distance_to_city',
    '#distance_to_town',
    'local_population_1km',
    'water_point_population',
    'pressure_score',
    'is_urban'
]

df = df[columns_to_keep]
df.columns = [c.replace('#', '').strip() for c in df.columns]
df.to_csv('wpdx_cleaned.csv', index=False)
