import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib
import time

class MLModelManager:
    def __init__(self):
        self.models = {
            'random_forest': RandomForestClassifier(n_estimators=100)
        }
    
    def train(self, X, y, validation_split=0.2):
        try:
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=validation_split, random_state=42
            )
            
            # Train model
            start_time = time.time()
            self.models['random_forest'].fit(X_train, y_train)
            training_time = time.time() - start_time
            
            # Validate
            val_pred = self.models['random_forest'].predict(X_val)
            accuracy = accuracy_score(y_val, val_pred)
            
            return {
                'success': True,
                'accuracy': accuracy,
                'training_time': training_time
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def predict(self, features):
        if isinstance(features, dict):
            features = np.array(list(features.values())).reshape(1, -1)
        return self.models['random_forest'].predict(features)
    
    def save(self, path):
        try:
            joblib.dump(self.models, path)
            return True
        except Exception as e:
            print(f"Save error: {e}")
            return False
    
    def load(self, path):
        try:
            self.models = joblib.load(path)
            return True
        except Exception as e:
            print(f"Load error: {e}")
            return False