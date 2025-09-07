#!/usr/bin/env python3
"""
Enhanced ML Models Module with Advanced Diagnostics
"""
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, classification_report, 
                           confusion_matrix)
from typing import List, Dict, Tuple
import time
import matplotlib.pyplot as plt

class MLModelManager:
    """Advanced ML model manager with comprehensive diagnostics"""
    
    def __init__(self):
        self.classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_split=5,
            min_samples_leaf=2,
            max_features='sqrt',
            class_weight='balanced_subsample',
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = None
    
    def train(self, training_data: List[Dict], validation_split: float = 0.2) -> Dict:
        """Enhanced training with comprehensive diagnostics"""
        try:
            start_time = time.time()
            
            # Convert to numpy arrays
            X = np.array([list(sample['features'].values()) for sample in training_data])
            y = np.array([sample['pattern_label'] for sample in training_data])
            self.feature_names = list(training_data[0]['features'].keys())
            
            # Train-test split
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, 
                test_size=validation_split,
                random_state=42,
                shuffle=True,
                stratify=y
            )
            
            # Feature scaling
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            
            # Model training
            self.classifier.fit(X_train_scaled, y_train)
            
            # Calculate metrics
            train_pred = self.classifier.predict(X_train_scaled)
            val_pred = self.classifier.predict(X_val_scaled)
            
            metrics = {
                'training_accuracy': accuracy_score(y_train, train_pred),
                'validation_accuracy': accuracy_score(y_val, val_pred),
                'training_report': classification_report(y_train, train_pred),
                'validation_report': classification_report(y_val, val_pred),
                'confusion_matrix': confusion_matrix(y_val, val_pred),
                'feature_importances': self._get_feature_importances(),
                'training_samples': len(X_train),
                'validation_samples': len(X_val),
                'training_time': time.time() - start_time
            }
            
            self.is_trained = True
            return {'success': True, **metrics}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_feature_importances(self) -> Dict[str, float]:
        """Get feature importance scores"""
        return dict(zip(self.feature_names, 
                       self.classifier.feature_importances_))
    
    def visualize_importances(self):
        """Plot feature importance diagram"""
        if not self.is_trained:
            raise RuntimeError("Model must be trained first")
            
        importances = self._get_feature_importances()
        sorted_features = sorted(importances.items(), key=lambda x: x[1], reverse=True)
        
        plt.figure(figsize=(10, 6))
        plt.barh([x[0] for x in sorted_features], [x[1] for x in sorted_features])
        plt.title("Feature Importances")
        plt.tight_layout()
        plt.show()
    
    def predict(self, features: Dict) -> int:
        """Make prediction on single sample"""
        if not self.is_trained:
            raise RuntimeError("Model must be trained before prediction")
        
        # Convert features to scaled numpy array
        X = np.array([list(features.values())])
        X_scaled = self.scaler.transform(X)
        return int(self.classifier.predict(X_scaled)[0])
    
    def save(self, path: str) -> bool:
        """Save trained models to disk"""
        if not self.is_trained:
            print("Warning: Saving untrained model")
            
        try:
            joblib.dump({
                'classifier': self.classifier,
                'scaler': self.scaler,
                'is_trained': self.is_trained
            }, path)
            return True
        except Exception as e:
            print(f"Error saving models: {e}")
            return False
    
    def load(self, path: str) -> bool:
        """Load pre-trained models from disk"""
        try:
            models = joblib.load(path)
            self.classifier = models['classifier']
            self.scaler = models['scaler']
            self.is_trained = models.get('is_trained', False)
            return True
        except Exception as e:
            print(f"Error loading models: {e}")
            return False