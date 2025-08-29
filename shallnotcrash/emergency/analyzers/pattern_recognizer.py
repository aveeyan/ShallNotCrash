#!/usr/bin/env python3
"""
Machine Learning Pattern Recognition for Emergency Detection
Phase 3 of the emergency detection algorithm
"""
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import IntEnum
import time
from collections import deque, defaultdict
import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import warnings
from .. import constants

class EmergencyPattern(IntEnum):
    """Emergency patterns identified by ML models"""
    NORMAL = 0
    ENGINE_DEGRADATION = 1
    FUEL_LEAK = 2
    STRUCTURAL_FATIGUE = 3
    ELECTRICAL_FAILURE = 4
    WEATHER_DISTRESS = 5
    SYSTEM_CASCADE = 6
    UNKNOWN_EMERGENCY = 7

class PatternConfidence(IntEnum):
    """Confidence levels for pattern recognition"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4

@dataclass
class PatternResult:
    """ML pattern recognition result"""
    pattern_type: EmergencyPattern
    confidence: PatternConfidence
    probability: float
    contributing_features: List[str]
    time_to_critical: Optional[float] = None
    recommended_action: str = "Monitor situation"
    severity_trend: float = 0.0
    anomaly_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

class PatternRecognizer:
    """Advanced ML-based pattern recognition for emergency detection"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.feature_window = 50
        self.prediction_horizon = 30
        
        self.feature_history = deque(maxlen=self.feature_window)
        self.pattern_history = deque(maxlen=100)
        
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
        self.pattern_classifier = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight='balanced')
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=15)
        
        self.emergency_signatures = {
            EmergencyPattern.ENGINE_DEGRADATION: {'features': ['rpm_trend', 'oil_pressure_trend', 'vibration_increase'], 'thresholds': {'rpm_trend': -50, 'oil_pressure_trend': -5, 'vibration_increase': 2.0}},
            EmergencyPattern.FUEL_LEAK: {'features': ['fuel_flow_asymmetry', 'fuel_level_drop_rate'], 'thresholds': {'fuel_flow_asymmetry': 0.3, 'fuel_level_drop_rate': 2.0}},
            EmergencyPattern.STRUCTURAL_FATIGUE: {'features': ['vibration_pattern', 'control_asymmetry', 'g_load_variance'], 'thresholds': {'vibration_pattern': 1.5, 'control_asymmetry': 0.2, 'g_load_variance': 0.5}},
            EmergencyPattern.SYSTEM_CASCADE: {'features': ['multi_system_correlation', 'failure_cascade_rate'], 'thresholds': {'multi_system_correlation': 0.8, 'failure_cascade_rate': 3.0}}
        }
        
        if model_path:
            self.load_models(model_path)
        
        self.is_trained = False
        self.last_prediction = None
        
    def extract_features(self, 
                        telemetry: Dict[str, float],
                        anomaly_scores: Dict[str, Any],
                        correlation_data: Dict[str, float]) -> np.ndarray:
        """Extract comprehensive features for ML models"""
        
        current_sample = {
            'telemetry': telemetry,
            'anomalies': anomaly_scores,
            'correlations': correlation_data,
            'timestamp': time.time()
        }
        self.feature_history.append(current_sample)
        
        if len(self.feature_history) < 10:
            return np.zeros(50)
        
        features = []
        features.extend(self._extract_statistical_features())
        features.extend(self._extract_trend_features())
        features.extend(self._extract_anomaly_features(anomaly_scores))
        features.extend(self._extract_correlation_features(correlation_data))
        features.extend(self._extract_temporal_features())
        features.extend(self._extract_interaction_features())
        
        # Pad with zeros if features are less than 50
        while len(features) < 50:
            features.append(0.0)
            
        return np.array(features[:50])
    
    def _extract_statistical_features(self) -> List[float]:
        """Extract statistical features from telemetry history"""
        features = []
        key_params = ['rpm', 'oil_pressure', 'fuel_flow', 'cht', 'vibration']
        
        for param in key_params:
            values = [sample['telemetry'].get(param, 0) for sample in self.feature_history]
            if len(values) >= 5:
                features.extend([np.mean(values), np.std(values), np.min(values), np.max(values)])
            else:
                features.extend([0, 0, 0, 0])
        return features[:20]
    
    def _extract_trend_features(self) -> List[float]:
        """Extract trend-based features"""
        features = []
        key_params = ['rpm', 'oil_pressure', 'fuel_flow', 'cht']
        
        for param in key_params:
            values = [sample['telemetry'].get(param, 0) for sample in self.feature_history]
            if len(values) >= 5:
                x = np.arange(len(values))
                slope = np.polyfit(x, values, 1)[0]
                rate_of_change = (values[-1] - values[0]) / len(values)
                features.extend([slope, rate_of_change])
            else:
                features.extend([0, 0])
        return features[:8]
    
    def _extract_anomaly_features(self, current_anomalies: Dict[str, Any]) -> List[float]:
        """Extract features from anomaly detection results"""
        features = []
        
        for param in ['rpm', 'oil_pressure', 'fuel_flow', 'cht']:
            if param in current_anomalies and hasattr(current_anomalies[param], 'normalized_score'):
                features.append(current_anomalies[param].normalized_score)
                features.append(float(current_anomalies[param].severity.value))
            else:
                features.extend([0, 0])
        
        anomaly_counts = defaultdict(int)
        for sample in list(self.feature_history)[-10:]:
            for param, anomaly in sample.get('anomalies', {}).items():
                if hasattr(anomaly, 'is_anomaly') and anomaly.is_anomaly:
                    anomaly_counts[param] += 1
        
        for param in ['rpm', 'oil_pressure', 'fuel_flow', 'cht']:
            features.append(anomaly_counts[param] / 10.0)
        return features[:12]
    
    def _extract_correlation_features(self, correlation_data: Dict[str, float]) -> List[float]:
        """Extract correlation-based features"""
        features = []
        system_pairs = ['engine-fuel', 'engine-structural', 'fuel-structural']
        for pair in system_pairs:
            features.append(correlation_data.get(pair, 0))
        
        max_corr = max(correlation_data.values()) if correlation_data else 0
        features.append(max_corr)
        
        corr_variance = np.var(list(correlation_data.values())) if correlation_data else 0
        features.append(corr_variance)
        return features[:5]
    
    def _extract_temporal_features(self) -> List[float]:
        """Extract time-based features"""
        features = []
        if len(self.feature_history) >= 2:
            current_time = time.time()
            last_change_time = current_time
            
            for i in range(len(self.feature_history) - 1, 0, -1):
                curr_sample = self.feature_history[i]
                prev_sample = self.feature_history[i-1]
                
                for param in ['rpm', 'oil_pressure', 'fuel_flow']:
                    curr_val = curr_sample['telemetry'].get(param, 0)
                    prev_val = prev_sample['telemetry'].get(param, 0)
                    
                    if abs(curr_val - prev_val) > 0.1 * abs(prev_val):
                        last_change_time = curr_sample['timestamp']
                        break
            features.append(current_time - last_change_time)
        else:
            features.append(0)
        
        change_rate = 0
        if len(self.feature_history) >= 5:
            recent_changes = 0
            for i in range(len(self.feature_history) - 4, len(self.feature_history)):
                if i > 0:
                    curr_anomalies = len(self.feature_history[i].get('anomalies', {}))
                    prev_anomalies = len(self.feature_history[i-1].get('anomalies', {}))
                    if curr_anomalies > prev_anomalies:
                        recent_changes += 1
            change_rate = recent_changes / 4.0
        features.append(change_rate)
        return features[:2]
    
    def _extract_interaction_features(self) -> List[float]:
        """Extract cross-system interaction features"""
        features = []
        if len(self.feature_history) >= 5:
            engine_fuel_interaction = 0
            #
            # ***** THE FIX IS HERE *****
            # Convert deque to list before slicing.
            #
            for sample in list(self.feature_history)[-5:]:
                rpm = sample['telemetry'].get('rpm', 0)
                fuel_flow = sample['telemetry'].get('fuel_flow', 0)
                if rpm > 0 and fuel_flow > 0:
                    engine_fuel_interaction += (rpm * fuel_flow) / 10000
            features.append(engine_fuel_interaction / 5.0)
            
            stability_score = 0
            for sample in list(self.feature_history)[-5:]:
                anomaly_count = sum(1 for a in sample.get('anomalies', {}).values() if hasattr(a, 'is_anomaly') and a.is_anomaly)
                stability_score += (5 - anomaly_count) / 5.0
            features.append(stability_score / 5.0)
        else:
            features.extend([0, 0])
        return features[:2]
    
    def predict_pattern(self, 
                       telemetry: Dict[str, float],
                       anomaly_scores: Dict[str, Any],
                       correlation_data: Dict[str, float]) -> PatternResult:
        """Predict emergency patterns using ML models"""
        
        features = self.extract_features(telemetry, anomaly_scores, correlation_data)
        
        if not self.is_trained:
            return self._rule_based_prediction(features, telemetry, anomaly_scores)
        
        features_2d = features.reshape(1, -1)
        
        # Preprocessing must match training
        features_scaled = self.scaler.transform(features_2d)
        features_reduced = self.pca.transform(features_scaled)
        
        anomaly_score = self.isolation_forest.decision_function(features_reduced)[0]
        
        probabilities = self.pattern_classifier.predict_proba(features_reduced)[0]
        pattern_idx = np.argmax(probabilities)
        confidence_score = probabilities[pattern_idx]
        
        pattern_type = EmergencyPattern(pattern_idx)
        
        if confidence_score >= 0.9: confidence = PatternConfidence.VERY_HIGH
        elif confidence_score >= 0.7: confidence = PatternConfidence.HIGH
        elif confidence_score >= 0.5: confidence = PatternConfidence.MEDIUM
        else: confidence = PatternConfidence.LOW
        
        recommended_action = self._get_recommended_action(pattern_type, confidence)
        time_to_critical = self._estimate_time_to_critical(pattern_type, features)
        contributing_features = self._identify_contributing_features(features, pattern_type)
        
        result = PatternResult(
            pattern_type=pattern_type,
            confidence=confidence,
            probability=float(confidence_score),
            contributing_features=contributing_features,
            time_to_critical=time_to_critical,
            recommended_action=recommended_action,
            severity_trend=self._calculate_severity_trend(),
            anomaly_score=abs(anomaly_score)
        )
        
        self.last_prediction = result
        self.pattern_history.append(result)
        return result
    
    def _rule_based_prediction(self, 
                              features: np.ndarray,
                              telemetry: Dict[str, float],
                              anomaly_scores: Dict[str, Any]) -> PatternResult:
        """Fallback rule-based prediction when ML models aren't trained"""
        critical_anomalies = [name for name, score in anomaly_scores.items() if hasattr(score, 'severity') and score.severity.value >= 3]
        
        if critical_anomalies:
            if 'rpm' in critical_anomalies or 'oil_pressure' in critical_anomalies:
                pattern_type = EmergencyPattern.ENGINE_DEGRADATION
            elif 'fuel_flow' in critical_anomalies:
                pattern_type = EmergencyPattern.FUEL_LEAK
            else:
                pattern_type = EmergencyPattern.UNKNOWN_EMERGENCY
            confidence = PatternConfidence.MEDIUM
            probability = 0.6
        else:
            pattern_type = EmergencyPattern.NORMAL
            confidence = PatternConfidence.HIGH
            probability = 0.8
        
        return PatternResult(
            pattern_type=pattern_type,
            confidence=confidence,
            probability=probability,
            contributing_features=critical_anomalies,
            recommended_action=self._get_recommended_action(pattern_type, confidence),
            severity_trend=0.0,
            anomaly_score=0.0
        )
    
    def _get_recommended_action(self, pattern: EmergencyPattern, confidence: PatternConfidence) -> str:
        """Generate recommended actions based on pattern and confidence"""
        actions = {
            EmergencyPattern.NORMAL: "Continue normal operations",
            EmergencyPattern.ENGINE_DEGRADATION: "REDUCE POWER - Prepare for engine failure",
            EmergencyPattern.FUEL_LEAK: "FUEL EMERGENCY - Land immediately",
            EmergencyPattern.STRUCTURAL_FATIGUE: "STRUCTURAL CONCERN - Reduce G-loads",
            EmergencyPattern.ELECTRICAL_FAILURE: "ELECTRICAL EMERGENCY - Use backup systems",
            EmergencyPattern.WEATHER_DISTRESS: "WEATHER EMERGENCY - Seek alternate route",
            EmergencyPattern.SYSTEM_CASCADE: "MULTIPLE SYSTEM FAILURE - Emergency landing",
            EmergencyPattern.UNKNOWN_EMERGENCY: "UNKNOWN EMERGENCY - Assess situation"
        }
        base_action = actions.get(pattern, "Monitor situation")
        if confidence == PatternConfidence.VERY_HIGH and pattern != EmergencyPattern.NORMAL:
            return f"IMMEDIATE ACTION: {base_action}"
        return base_action
    
    def _estimate_time_to_critical(self, pattern: EmergencyPattern, features: np.ndarray) -> Optional[float]:
        """Estimate time until critical condition"""
        if pattern == EmergencyPattern.NORMAL:
            return None
        
        if len(self.feature_history) >= 10:
            severity_values = []
            #
            # ***** THE FIX IS HERE *****
            # Convert deque to list before slicing.
            #
            for sample in list(self.feature_history)[-10:]:
                max_severity = max((a.severity.value for a in sample.get('anomalies', {}).values() if hasattr(a, 'severity')), default=0)
                severity_values.append(max_severity)
            
            if len(severity_values) >= 5:
                trend = np.polyfit(range(len(severity_values)), severity_values, 1)[0]
                if trend > 0:
                    current_severity = severity_values[-1]
                    time_to_critical = (4 - current_severity) / trend
                    return max(0, min(3600, time_to_critical))
        return None
    
    def _identify_contributing_features(self, features: np.ndarray, pattern: EmergencyPattern) -> List[str]:
        """Identify which features contribute most to the pattern"""
        if pattern in self.emergency_signatures:
            return self.emergency_signatures[pattern]['features']
        
        feature_names = ['rpm_mean', 'oil_pressure_mean', 'fuel_flow_mean', 'cht_mean', 'vibration_mean', 'rpm_trend', 'oil_pressure_trend']
        if len(features) >= len(feature_names):
            top_indices = np.argsort(np.abs(features[:len(feature_names)]))[-3:]
            return [feature_names[i] for i in top_indices]
        return ['insufficient_data']
    
    def _calculate_severity_trend(self) -> float:
        """Calculate trend in overall severity"""
        if len(self.pattern_history) >= 5:
            recent_patterns = list(self.pattern_history)[-5:]
            severity_values = [p.pattern_type.value for p in recent_patterns]
            if len(severity_values) >= 3:
                x = np.arange(len(severity_values))
                trend = np.polyfit(x, severity_values, 1)[0]
                return trend
        return 0.0
    
    def train_models(self, training_data: List[Dict[str, Any]]):
        """Train ML models with historical data"""
        if len(training_data) < 100:
            warnings.warn("Insufficient training data for ML models")
            return
        
        X, y = [], []
        
        # Reset history before processing training data
        self.feature_history.clear()
        
        for sample in training_data:
            features = self.extract_features(sample['telemetry'], sample['anomaly_scores'], sample['correlation_data'])
            X.append(features)
            y.append(sample['pattern_label'])
        
        X = np.array(X)
        y = np.array(y)
        
        X_scaled = self.scaler.fit_transform(X)
        X_reduced = self.pca.fit_transform(X_scaled)
        
        self.isolation_forest.fit(X_reduced)
        self.pattern_classifier.fit(X_reduced, y)
        self.is_trained = True
    
    def save_models(self, path: str):
        """Save trained models"""
        model_data = {'isolation_forest': self.isolation_forest, 'pattern_classifier': self.pattern_classifier, 'scaler': self.scaler, 'pca': self.pca, 'is_trained': self.is_trained}
        joblib.dump(model_data, path)
    
    def load_models(self, path: str):
        """Load pre-trained models"""
        try:
            model_data = joblib.load(path)
            self.isolation_forest = model_data['isolation_forest']
            self.pattern_classifier = model_data['pattern_classifier']
            self.scaler = model_data['scaler']
            self.pca = model_data['pca']
            self.is_trained = model_data['is_trained']
        except FileNotFoundError:
            warnings.warn(f"Model file not found: {path}")

PATTERN_RECOGNIZER = PatternRecognizer()

def recognize_patterns(telemetry: Dict[str, float],
                      anomaly_scores: Dict[str, Any],
                      correlation_data: Dict[str, float]) -> PatternResult:
    """Public interface for pattern recognition"""
    return PATTERN_RECOGNIZER.predict_pattern(telemetry, anomaly_scores, correlation_data)
