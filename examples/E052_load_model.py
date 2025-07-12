import joblib
try:
    model = joblib.load("models/c172p_emergency_model.joblib")
    print("Model loaded successfully")
    print(f"Model contents: {list(model.keys())}")
except Exception as e:
    print(f"Model corrupted: {str(e)}")