#!/usr/bin/env python3
"""
Advanced Emergency Pattern Recognition Training System
"""
import numpy as np
import os
import time
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# Try to import required dependencies with fallbacks
try:
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.metrics import classification_report, confusion_matrix
    import pandas as pd
    from scipy import stats
    sklearn_available = True
except ImportError:
    print("Warning: sklearn, pandas, or scipy not available. Some features will be limited.")
    sklearn_available = False

# Try to import the custom modules - provide fallbacks if not available
try:
    from pr1_pattern_types import (
        EmergencyPattern,
        AnomalyScore,
        AnomalySeverity,
        EMERGENCY_SIGNATURES
    )
    from pr2_feature_extractor import FeatureExtractor
    from pr3_ml_models import MLModelManager
    custom_modules_available = True
except ImportError:
    print("Warning: Custom modules not available. Creating fallback implementations.")
    custom_modules_available = False

# Fallback implementations if custom modules are not available
if not custom_modules_available:
    from enum import Enum
    from dataclasses import dataclass
    
    class EmergencyPattern(Enum):
        NORMAL = 0
        ENGINE_DEGRADATION = 1
        FUEL_LEAK = 2
        STRUCTURAL_FATIGUE = 3
    
    class AnomalySeverity(Enum):
        NORMAL = 0
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        CRITICAL = 4
    
    @dataclass
    class AnomalyScore:
        is_anomaly: bool
        normalized_score: float
        severity: AnomalySeverity
    
    EMERGENCY_SIGNATURES = {
        EmergencyPattern.NORMAL: {'rpm': (2100, 2500), 'oil': (30, 40)},
        EmergencyPattern.ENGINE_DEGRADATION: {'rpm': (1800, 2200), 'oil': (20, 35)},
        EmergencyPattern.FUEL_LEAK: {'rpm': (1900, 2300), 'oil': (25, 40)},
        EmergencyPattern.STRUCTURAL_FATIGUE: {'rpm': (2000, 2400), 'oil': (25, 40)}
    }
    
    class FeatureExtractor:
        def __init__(self, window_size: int = 30):
            self.window_size = window_size
        
        def extract(self, telemetry: Dict, anomalies: Dict, correlation_data: Dict) -> Dict:
            """Extract features from telemetry data"""
            features = {}
            
            # Basic telemetry features
            for key, value in telemetry.items():
                if isinstance(value, (int, float)):
                    features[f'{key}_value'] = float(value)
                    features[f'{key}_normalized'] = self._normalize_value(key, value)
            
            # Anomaly features
            for key, anomaly in anomalies.items():
                features[f'{key}_anomaly'] = float(anomaly.is_anomaly)
                features[f'{key}_score'] = float(anomaly.normalized_score)
                features[f'{key}_severity'] = float(anomaly.severity.value)
            
            # Correlation features
            for key, corr in correlation_data.items():
                features[f'corr_{key}'] = float(corr)
            
            return features
        
        def _normalize_value(self, key: str, value: float) -> float:
            """Normalize telemetry values to 0-1 range"""
            ranges = {
                'rpm': (1500, 2900),
                'oil_pressure': (15, 50),
                'vibration': (0.1, 5.0),
                'cht': (200, 400),
                'fuel_flow': (8, 25),
                'altitude': (0, 10000)
            }
            
            if key in ranges:
                min_val, max_val = ranges[key]
                return (value - min_val) / (max_val - min_val)
            return value
    
    class MLModelManager:
        def __init__(self):
            if sklearn_available:
                from sklearn.ensemble import RandomForestClassifier
                from sklearn.preprocessing import StandardScaler
                from sklearn.pipeline import Pipeline
                
                self.classifier = Pipeline([
                    ('scaler', StandardScaler()),
                    ('rf', RandomForestClassifier(
                        n_estimators=100,
                        max_depth=10,
                        random_state=42,
                        n_jobs=-1
                    ))
                ])
            else:
                self.classifier = None
        
        def train(self, processed_data: List[Dict], validation_split: float = 0.2) -> Dict:
            """Train the ML model"""
            if not sklearn_available:
                return {'success': False, 'error': 'sklearn not available'}
            
            # Prepare data
            X = np.array([list(sample['features'].values()) for sample in processed_data])
            y = np.array([sample['pattern_label'] for sample in processed_data])
            
            # Split data
            split_idx = int(len(X) * (1 - validation_split))
            X_train, X_val = X[:split_idx], X[split_idx:]
            y_train, y_val = y[:split_idx], y[split_idx:]
            
            # Train model
            self.classifier.fit(X_train, y_train)
            
            # Evaluate
            train_accuracy = self.classifier.score(X_train, y_train)
            val_accuracy = self.classifier.score(X_val, y_val)
            
            y_pred = self.classifier.predict(X_val)
            val_report = classification_report(y_val, y_pred)
            
            return {
                'success': True,
                'training_accuracy': train_accuracy,
                'validation_accuracy': val_accuracy,
                'validation_report': val_report
            }
        
        def save(self, path: str) -> bool:
            """Save the trained model"""
            try:
                import joblib
                joblib.dump(self.classifier, path)
                return True
            except Exception as e:
                print(f"Error saving model: {e}")
                return False
        
        def visualize_importances(self) -> None:
            """Visualize feature importances"""
            if not sklearn_available or not hasattr(self.classifier, 'named_steps'):
                print("Feature importance visualization not available")
                return
            
            try:
                rf_model = self.classifier.named_steps['rf']
                importances = rf_model.feature_importances_
                
                plt.figure(figsize=(10, 6))
                indices = np.argsort(importances)[::-1][:15]  # Top 15 features
                
                plt.title("Feature Importances")
                plt.bar(range(len(indices)), importances[indices])
                plt.xticks(range(len(indices)), [f'Feature_{i}' for i in indices], rotation=45)
                plt.tight_layout()
                plt.show()
            except Exception as e:
                print(f"Error visualizing importances: {e}")

# Constants
PATTERN_SAMPLES = 200  # Samples per emergency pattern
WINDOW_SIZE = 30       # For temporal feature extraction

def generate_training_data() -> List[Dict]:
    """
    Generate realistic training data with overlapping patterns and noise
    """
    samples = []
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # More realistic base parameters with overlapping ranges
    base_normal = {'rpm': 2300, 'oil': 35, 'vib': 0.8, 'fuel': 15, 'cht': 300}
    
    # Add environmental noise factors
    environmental_factors = {
        'altitude_factor': lambda alt: 1.0 + (alt - 5000) / 10000 * 0.1,
        'temperature_factor': lambda temp: 1.0 + (temp - 20) / 50 * 0.05,
        'age_factor': lambda: np.random.uniform(0.9, 1.1)  # Aircraft age variation
    }
    
    for pattern in [EmergencyPattern.NORMAL, EmergencyPattern.ENGINE_DEGRADATION, 
                   EmergencyPattern.FUEL_LEAK, EmergencyPattern.STRUCTURAL_FATIGUE]:
        
        for _ in range(PATTERN_SAMPLES):
            # Environmental conditions
            altitude = np.random.normal(5000, 2000)
            temperature = np.random.normal(20, 15)
            age_factor = environmental_factors['age_factor']()
            alt_factor = environmental_factors['altitude_factor'](altitude)
            temp_factor = environmental_factors['temperature_factor'](temperature)
            
            # Add sensor noise and drift
            sensor_noise = {
                'rpm': np.random.normal(0, 25),
                'oil': np.random.normal(0, 1.5),
                'vib': np.random.normal(0, 0.15),
                'fuel': np.random.normal(0, 0.8),
                'cht': np.random.normal(0, 8)
            }
            
            # Pattern-specific modifications with realistic overlap
            if pattern == EmergencyPattern.NORMAL:
                rpm_base = base_normal['rpm'] * alt_factor * age_factor
                oil_base = base_normal['oil'] * temp_factor * age_factor
                vib_base = base_normal['vib'] * age_factor
                fuel_base = base_normal['fuel'] * alt_factor
                cht_base = base_normal['cht'] * temp_factor
                
            elif pattern == EmergencyPattern.ENGINE_DEGRADATION:
                # Gradual degradation - not always severe
                degradation_severity = np.random.uniform(0.1, 0.8)
                rpm_base = base_normal['rpm'] * (1 - degradation_severity * 0.3) * alt_factor
                oil_base = base_normal['oil'] * (1 - degradation_severity * 0.4) * temp_factor
                vib_base = base_normal['vib'] * (1 + degradation_severity * 2.5) * age_factor
                fuel_base = base_normal['fuel'] * (1 + degradation_severity * 0.2) * alt_factor
                cht_base = base_normal['cht'] * (1 + degradation_severity * 0.15) * temp_factor
                
            elif pattern == EmergencyPattern.FUEL_LEAK:
                # Fuel leak affects multiple systems
                leak_severity = np.random.uniform(0.2, 0.9)
                rpm_base = base_normal['rpm'] * (1 - leak_severity * 0.15) * alt_factor
                oil_base = base_normal['oil'] * (0.9 + np.random.uniform(-0.1, 0.1)) * temp_factor
                vib_base = base_normal['vib'] * (1 + leak_severity * 0.5) * age_factor
                fuel_base = base_normal['fuel'] * (1 + leak_severity * 1.2) * alt_factor  # Compensating flow
                cht_base = base_normal['cht'] * (1 + leak_severity * 0.1) * temp_factor
                
            elif pattern == EmergencyPattern.STRUCTURAL_FATIGUE:
                # Structural issues show up in vibration and control response
                fatigue_level = np.random.uniform(0.3, 0.9)
                rpm_base = base_normal['rpm'] * (0.95 + np.random.uniform(-0.05, 0.05)) * alt_factor
                oil_base = base_normal['oil'] * (0.9 + np.random.uniform(-0.2, 0.2)) * temp_factor
                vib_base = base_normal['vib'] * (1 + fatigue_level * 3.0) * age_factor
                fuel_base = base_normal['fuel'] * (1 + np.random.uniform(-0.1, 0.1)) * alt_factor
                cht_base = base_normal['cht'] * (1 + np.random.uniform(-0.05, 0.05)) * temp_factor
            
            # Apply realistic variance and limits
            telemetry = {
                'rpm': np.clip(
                    np.random.normal(rpm_base, 80) + sensor_noise['rpm'], 
                    1500, 2900
                ),
                'oil_pressure': np.clip(
                    np.random.normal(oil_base, 4) + sensor_noise['oil'], 
                    15, 50
                ),
                'vibration': np.clip(
                    np.random.normal(vib_base, 0.4) + sensor_noise['vib'], 
                    0.1, 5.0
                ),
                'cht': np.clip(
                    np.random.normal(cht_base, 25) + sensor_noise['cht'], 
                    200, 400
                ),
                'fuel_flow': np.clip(
                    np.random.normal(fuel_base, 3) + sensor_noise['fuel'], 
                    8, 25
                ),
                'altitude': altitude,
            }
            
            # More realistic anomaly scoring with false positives/negatives
            def calculate_anomaly_score(value, normal_range, noise_factor=0.2):
                if normal_range[1] == normal_range[0]:
                    return 0.0
                normalized = abs(value - normal_range[0]) / (normal_range[1] - normal_range[0])
                # Add noise to make it less perfect
                noise = np.random.uniform(-noise_factor, noise_factor)
                return np.clip(normalized + noise, 0, 1)
            
            anomalies = {
                'rpm': AnomalyScore(
                    is_anomaly=pattern != EmergencyPattern.NORMAL and np.random.random() > 0.15,  # 15% false negatives
                    normalized_score=calculate_anomaly_score(telemetry['rpm'], (2100, 2500)),
                    severity=AnomalySeverity.NORMAL
                ),
                'oil_pressure': AnomalyScore(
                    is_anomaly=pattern != EmergencyPattern.NORMAL and np.random.random() > 0.1,  # 10% false negatives
                    normalized_score=calculate_anomaly_score(telemetry['oil_pressure'], (30, 40)),
                    severity=AnomalySeverity.NORMAL
                )
            }
            
            # Add some normal samples with false positive anomalies
            if pattern == EmergencyPattern.NORMAL and np.random.random() < 0.08:  # 8% false positives
                anomalies['rpm'].is_anomaly = True
                anomalies['rpm'].normalized_score = np.random.uniform(0.3, 0.7)
            
            # More realistic correlation data with noise
            base_correlations = {
                'engine-fuel': 0.3 + np.random.normal(0, 0.15),
                'engine-structural': 0.2 + np.random.normal(0, 0.2)
            }
            
            # Pattern-specific correlation adjustments
            if pattern == EmergencyPattern.ENGINE_DEGRADATION:
                base_correlations['engine-fuel'] += np.random.uniform(0.2, 0.5)
            elif pattern == EmergencyPattern.FUEL_LEAK:
                base_correlations['engine-fuel'] += np.random.uniform(0.3, 0.6)
            elif pattern == EmergencyPattern.STRUCTURAL_FATIGUE:
                base_correlations['engine-structural'] += np.random.uniform(0.3, 0.6)
            
            # Clip correlations to valid range
            correlation_data = {
                k: np.clip(v, -0.1, 1.0) for k, v in base_correlations.items()
            }
            
            samples.append({
                'telemetry': telemetry,
                'anomaly_scores': anomalies,
                'correlation_data': correlation_data,
                'pattern_label': pattern.value
            })
    
    # Shuffle to avoid any ordering bias
    np.random.shuffle(samples)
    return samples

def visualize_data_characteristics(processed_data: List[Dict]) -> None:
    """
    Generate comprehensive visualizations of training data
    Args:
        processed_data: List of processed training samples
    """
    if not sklearn_available:
        print("Visualization requires pandas and scipy. Skipping...")
        return
    
    try:
        import pandas as pd
        from scipy import stats
        
        df = pd.DataFrame([sample['features'] for sample in processed_data])
        df['label'] = [EmergencyPattern(sample['pattern_label']).name for sample in processed_data]
        
        # 1. Feature Distribution Plot
        plt.figure(figsize=(15, 10))
        feature_cols = ['rpm_value', 'oil_pressure_value', 'vibration_value']
        available_features = [col for col in feature_cols if col in df.columns]
        
        for i, feature in enumerate(available_features, 1):
            plt.subplot(len(available_features), 1, i)
            for label in df['label'].unique():
                subset = df[df['label'] == label][feature]
                if len(subset) > 1:
                    density = stats.gaussian_kde(subset)
                    xs = np.linspace(subset.min(), subset.max(), 200)
                    plt.plot(xs, density(xs), label=label)
            plt.title(f'{feature} Distribution')
            plt.legend()
        plt.tight_layout()
        plt.show()

        # 2. Feature Correlation Matrix
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            
            plt.figure(figsize=(12, 10))
            plt.imshow(corr_matrix, cmap='coolwarm', aspect='auto')
            plt.colorbar()
            plt.title('Feature Correlation Matrix')
            plt.xticks(range(len(corr_matrix.columns)), corr_matrix.columns, rotation=90)
            plt.yticks(range(len(corr_matrix.columns)), corr_matrix.columns)
            plt.tight_layout()
            plt.show()
    except Exception as e:
        print(f"Error in visualization: {e}")

def train_and_evaluate_model() -> Dict:
    """
    Complete model training and evaluation workflow
    Returns:
        Dictionary containing training results and metrics
    """
    # Initialize components
    feature_extractor = FeatureExtractor(window_size=WINDOW_SIZE)
    ml_models = MLModelManager()

    # 1. Data Preparation
    print("Generating training data...")
    start_time = time.time()
    raw_data = generate_training_data()
    
    print("Extracting features...")
    processed_data = []
    for sample in raw_data:
        try:
            features = feature_extractor.extract(
                telemetry=sample['telemetry'],
                anomalies=sample['anomaly_scores'],
                correlation_data=sample['correlation_data']
            )
            processed_data.append({
                'features': features,
                'pattern_label': sample['pattern_label']
            })
        except Exception as e:
            print(f"Error processing sample: {e}")
            continue
    
    print(f"Data preparation completed in {time.time() - start_time:.2f}s")
    print(f"Generated {len(processed_data)} samples")

    # 2. Data Analysis
    try:
        visualize_data_characteristics(processed_data)
    except Exception as e:
        print(f"Visualization error: {e}")

    # 3. Model Training
    print("\nTraining ML models...")
    
    if sklearn_available and len(processed_data) > 0:
        X = np.array([list(sample['features'].values()) for sample in processed_data])
        y = np.array([sample['pattern_label'] for sample in processed_data])

        # Enhanced Cross-Validation
        try:
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            cv_scores = cross_val_score(
                ml_models.classifier, X, y,
                cv=cv, n_jobs=-1, scoring='accuracy'
            )
            print(f"\nCross-validation scores: {cv_scores}")
            print(f"Mean CV accuracy: {cv_scores.mean():.2f} (±{cv_scores.std():.2f})")
        except Exception as e:
            print(f"Cross-validation error: {e}")

        # Full training with validation
        train_results = ml_models.train(processed_data, validation_split=0.2)
        
        if not train_results['success']:
            raise RuntimeError(f"Training failed: {train_results.get('error')}")

        # 4. Model Analysis
        print("\n=== Training Report ===")
        print(f"Training accuracy: {train_results['training_accuracy']:.2f}")
        print(f"Validation accuracy: {train_results['validation_accuracy']:.2f}")
        print("\nClassification Report:")
        print(train_results['validation_report'])
        
        # Feature Importance Analysis
        try:
            ml_models.visualize_importances()
        except Exception as e:
            print(f"Feature importance visualization error: {e}")

        # 5. Model Persistence
        model_path = "models/c172p_emergency_model.joblib"
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        if ml_models.save(model_path):
            print(f"\nModel saved to {model_path}")
        else:
            print("\nModel saving failed")

        return train_results
    else:
        print("Training skipped - sklearn not available or no data")
        return {'success': False, 'error': 'Training requirements not met'}

def main():
    """Main function with error handling"""
    try:
        results = train_and_evaluate_model()
        if results['success']:
            print("\n=== Training Completed Successfully ===")
        else:
            print(f"\n=== Training Failed: {results.get('error', 'Unknown error')} ===")
    except Exception as e:
        print(f"\n=== Critical Error: {e} ===")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()