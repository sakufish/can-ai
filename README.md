***About***
This project uses AI to predict local water access in underserved regions, helping address data gaps in communities often left out of national statistics. We focus on generating reliable, per-kilometer-square water access scores by combining satellite imagery with geospatial data.
We applied our model to regions in Kenya and Uganda, but the system is generalizable to other parts of the world.

*** Key Features ***
- Combines satellite imagery (Sentinel-2) and tabular geospatial features
- Uses a CNN + MLP fusion model to generate water access scores
- Backend built with Flask for real-time predictions
- Frontend built with React + TypeScript to visualize results
- Integrated with Google Earth Engine for data collection
