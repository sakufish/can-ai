import os
import joblib
import torch
import torch.nn as nn
from torchvision import models, transforms
from flask import Flask, request, jsonify
from PIL import Image
import numpy as np
import json
from flask_cors import CORS


# --------------------------
# model definition
# --------------------------
class CNNTFMModel(nn.Module):
    def __init__(self, tabular_dim):
        super().__init__()

        resnet = models.resnet18(pretrained=True)
        self.cnn = nn.Sequential(*list(resnet.children())[:-1])
        self.cnn_out_dim = resnet.fc.in_features

        self.fc = nn.Sequential(
            nn.Linear(self.cnn_out_dim + tabular_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 1)
        )

    def forward(self, image, tabular):
        cnn_feat = self.cnn(image)
        cnn_feat = cnn_feat.view(image.size(0), -1)
        x = torch.cat((cnn_feat, tabular), dim=1)
        return self.fc(x).squeeze()

# --------------------------
# Configurations
# --------------------------
MODEL_PATH = "model/best_model.pth"  
FEATURE_SCALER_PATH = "scalers/feature_scaler.pkl"
SCORE_SCALER_PATH = "scalers/score_scaler.pkl"

TABULAR_FEATURES = [
   'elevation', 'land_cover_class', 'mean_distance_to_water', 'mean_ndvi', 'nighttime_light', 'slope'
]


# --------------------------
# load Model and scalers
# --------------------------
feature_scaler = joblib.load(FEATURE_SCALER_PATH)
score_scaler = joblib.load(SCORE_SCALER_PATH)

tabular_dim = len(TABULAR_FEATURES)
model = CNNTFMModel(tabular_dim=tabular_dim)
model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
model.eval()

# --------------------------
# image preprocessing
# --------------------------
img_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# --------------------------
# app
# --------------------------
app = Flask(__name__)
CORS(app)

@app.route("/predict/", methods=["POST"])
def predict():
    if "image" not in request.files or "features" not in request.form:
        return jsonify({"error": "Provide both image and features"}), 400

    # load and transform image
    image_file = request.files["image"]
    image = Image.open(image_file).convert("RGB")
    img_tensor = img_transform(image).unsqueeze(0)  # (1, 3, 224, 224)

    # parse the tabular features
    features_json = request.form["features"]
    features = json.loads(features_json)
    try:
        feature_vector = np.array([features[feat] for feat in TABULAR_FEATURES], dtype=np.float32).reshape(1, -1)
    except KeyError as e:
        return jsonify({"error": f"Missing feature: {e}"}), 400

    # scale features
    scaled_tabular = feature_scaler.transform(feature_vector)
    tab_tensor = torch.from_numpy(scaled_tabular).float()

    # predict
    with torch.no_grad():
        pred = model(img_tensor, tab_tensor)
        pred = pred.item()
        pred_score = score_scaler.inverse_transform([[pred]])[0][0]

    return jsonify({"predicted_score": float(pred_score)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
