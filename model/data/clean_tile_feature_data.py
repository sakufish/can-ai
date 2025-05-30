from sklearn.preprocessing import StandardScaler
import pandas as pd

# load the csv as a dataframe
df = pd.read_csv('tile_features.csv')

# drop
df = df.drop(columns=[
    'system:index',
    'category_bonus',
    'distance_weighted_score',
    'norm_distance_weighted',
    'num_sources',
    'pressure_score',
    'random',
    'water_point_population',
    'water_source_category',
    '.geo'
])

# isolate features from label
features = df.drop(['tile_id', 'score'], axis=1)
scores = df['score'].values.reshape(-1, 1)

# scale features and label
feature_scaler = StandardScaler()
score_scaler = StandardScaler()

scaled_features = feature_scaler.fit_transform(features)
scaled_scores = score_scaler.fit_transform(scores)

# add to new dataframe
df_scaled = df.copy()
df_scaled[features.columns] = scaled_features
df_scaled['score'] = scaled_scores

"""
df_scaled.to_csv('tile_features_scaled.csv', index=False)
"""


import joblib

# save scalers
joblib.dump(feature_scaler, 'feature_scaler.pkl')
joblib.dump(score_scaler, 'score_scaler.pkl')

print("scalers saved!")
