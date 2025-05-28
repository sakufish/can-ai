import pandas as pd
from sklearn.neighbors import KNeighborsRegressor
import numpy as np

# --- load and filter valid entries ---
df = pd.read_csv('raw.csv', encoding='utf-8', low_memory=False)

# --- make sure lat/lon are numeric and valid ---
df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
df = df.dropna(subset=['latitude', 'longitude'])

# --- only include western kenya ---
df = df[
    (df['latitude'] > -1.5) & (df['latitude'] < 0.8) &
    (df['longitude'] > 34.89) & (df['longitude'] < 36.29)
]

# --- keep relevant columns ---
columns_to_keep = [
    'latitude',
    'longitude',
    '#status_id',
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
columns_to_keep = [col for col in columns_to_keep if col in df.columns]
df = df[columns_to_keep]
df.columns = [c.replace('#', '').strip() for c in df.columns]

# --- identify numeric columns ---
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
numeric_cols = [col for col in numeric_cols if col not in ['latitude', 'longitude']]

# --- fill missing water source categories ---
df['water_source_category'] = df['water_source_category'].fillna('unknown').replace('', 'unknown')

# --- KNN impute all numeric columns ---
for col in numeric_cols:
    known = df[df[col].notna()]
    unknown = df[df[col].isna()]

    if not unknown.empty and len(known) >= 3:
        knn = KNeighborsRegressor(n_neighbors=5, weights='distance')
        knn.fit(known[['latitude', 'longitude']], known[col])
        df.loc[unknown.index, col] = knn.predict(unknown[['latitude', 'longitude']])

# --- clean boolean column ---
if 'is_urban' in df.columns:
    df['is_urban'] = df['is_urban'].astype(str).str.lower()
    df['is_urban'] = df['is_urban'].where(df['is_urban'].isin(['true', 'false']), 'false')

# --- export cleaned version ---
df.to_csv('wpdx_cleaned4.csv', index=False)
