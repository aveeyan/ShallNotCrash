import joblib
import numpy as np

from train_emergency_detector import (
    FeatureExtractor,
    AnomalyScore,
    AnomalySeverity,
    EmergencyPattern
)

# Show available severity levels
print(list(AnomalySeverity))

# Load model from joblib (may be a dict)
MODEL_PATH = "models/c172p_emergency_model.joblib"
loaded_obj = joblib.load(MODEL_PATH)
print("Loaded object type:", type(loaded_obj))

# Handle dict model storage
if isinstance(loaded_obj, dict):
    print("Available keys:", loaded_obj.keys())
    model = loaded_obj.get("model") or loaded_obj.get("classifier") or next(iter(loaded_obj.values()))
else:
    model = loaded_obj

# === Sample telemetry ===
telemetry = {
    'rpm': 2150,
    'oil_pressure': 31,
    'vibration': 1.05,
    'cht': 295,
    'fuel_flow': 14,
    'altitude': 4500
}

# === Sample anomaly scores ===
anomalies = {
    'rpm': AnomalyScore(True, 0.6, AnomalySeverity.MODERATE),
    'oil_pressure': AnomalyScore(False, 0.2, AnomalySeverity.MINOR)
}

# === Correlation input ===
correlation_data = {
    'engine-fuel': 0.4,
    'engine-structural': 0.3
}

# === Feature extraction ===
extractor = FeatureExtractor()
features = extractor.extract(telemetry, anomalies, correlation_data)
X = np.array([list(features.values())])  # 2D input

# === Prediction ===
y_pred = model.predict(X)[0]
predicted_pattern = EmergencyPattern(y_pred).name

print(f"Predicted Emergency Pattern: {predicted_pattern}")
