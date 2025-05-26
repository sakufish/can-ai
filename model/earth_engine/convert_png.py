import os
import rasterio
from PIL import Image
import numpy as np

# --- directories ---
src_dir = "./exports"
dst_dir = "./converted_png"

os.makedirs(dst_dir, exist_ok=True)

# --- convert tif to png ---
for fname in os.listdir(src_dir):
    if fname.endswith(".tif"):
        with rasterio.open(os.path.join(src_dir, fname)) as src:
            arr = src.read([1, 2, 3])
            arr = np.transpose(arr, (1, 2, 0))
            arr = (arr / 3000.0).clip(0, 1) * 255
            arr = arr.astype(np.uint8)
            out_name = fname.replace(".tif", ".png")
            Image.fromarray(arr).save(os.path.join(dst_dir, out_name))
