***About***

This project uses AI to predict local water access in under represented regions, helping address data gaps in communities often left out of national statistics. We focus on generating reliable, per-kilometer-square water access scores by combining satellite imagery with geospatial data.
We applied our model to regions in Kenya and Uganda, but the system is generalizable to other parts of the world.

***Key Features***

- Combines satellite imagery (Sentinel-2) and tabular geospatial features
- Uses a CNN + MLP fusion model to generate water access scores
- Backend built with Flask for real-time predictions
- Frontend built with React + TypeScript to visualize results
- Integrated with Google Earth Engine for data collection

***How it works***

We started by generating thousands of 1km² tiles over Kenya and Uganda using Google Earth Engine. For each tile, we collected both satellite imagery (Sentinel-2) and various geospatial features, such as elevation, vegetation index (NDVI), land cover type, nighttime light levels, and distances to roads, rivers, and water bodies. We also pulled functional water point data from WPDx and calculated a custom water access score that considers infrastructure quality, population served, physical distance to water, and the type of water source. Our model combines a pre-trained ResNet18 (to process satellite images) with tabular data using a custom fusion neural network that outputs a single water equity score per tile. The system was trained using HuberLoss for robustness against outliers and optimized using Adam. Predictions are served via a Flask API, and our frontend—built with React and MapLibre—allows users to upload tile data, run batch predictions, and explore the results interactively on a map.

***notes***
- Render Free often runs out of memory when starting up with the model
- Stadia Maps membership lasts for 14 days
