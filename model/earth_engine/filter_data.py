import pandas as pd

# --- load and filter valid entries ---
df = pd.read_csv('../data/raw.csv', encoding='utf-8', low_memory=False)

# ensure lat/lon are numeric and drop invalids
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

# --- keep only available columns ---
columns_to_keep = [col for col in columns_to_keep if col in df.columns]
df = df[columns_to_keep]

df.columns = [c.replace('#', '').strip() for c in df.columns]

# --- clean data types ---
numeric_cols = [
    'distance_to_primary_road', 'distance_to_secondary_road',
    'distance_to_tertiary_road', 'distance_to_city', 'distance_to_town',
    'local_population_1km', 'water_point_population', 'pressure_score'
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

if 'is_urban' in df.columns:
    df['is_urban'] = df['is_urban'].astype(str).str.lower().replace({'true': 'true', 'false': 'false'})
    df['is_urban'] = df['is_urban'].where(df['is_urban'].isin(['true', 'false']), 'false')

df.to_csv('wpdx_cleaned2.csv', index=False)
