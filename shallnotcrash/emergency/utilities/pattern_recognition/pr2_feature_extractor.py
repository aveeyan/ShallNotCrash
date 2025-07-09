#!/usr/bin/env python3
"""
Feature Extractor - Updated for pattern types integration
"""
from pr1_pattern_types import TelemetryData, AnomalyScore
from typing import Union, Dict, Optional
import numpy as np

class FeatureExtractor:
    def __init__(self, window_size=10):
        self.window_size = window_size
        self.feature_history = []
        self.feature_names = [
            'rpm_value', 
            'oil_pressure_value',
            'vibration_value',
            'rpm_anomaly',
            'oil_anomaly',
            'engine_fuel_corr',
            'engine_struct_corr',
            'rpm_trend',
            'vibration_increase',
            'anomaly_persistence'
        ]
    
    def extract(self, telemetry, anomalies, correlation_data=None):
        """Ensure all feature vectors have consistent structure"""
        # Convert inputs to dict if needed
        tel_dict = telemetry if isinstance(telemetry, dict) else telemetry.to_dict()
        anomalies = self._ensure_anomaly_dict(anomalies)
        
        # Initialize feature dict with default values
        features = {name: 0.0 for name in self.feature_names}
        
        # Basic features
        features.update({
            'rpm_value': tel_dict.get('rpm', 0),
            'oil_pressure_value': tel_dict.get('oil_pressure', 0),
            'vibration_value': tel_dict.get('vibration', 0),
            'rpm_anomaly': anomalies.get('rpm', AnomalyScore(False, 0, 0)).normalized_score,
            'oil_anomaly': anomalies.get('oil_pressure', AnomalyScore(False, 0, 0)).normalized_score
        })
        
        # Correlation features
        if correlation_data:
            features.update({
                'engine_fuel_corr': correlation_data.get('engine-fuel', 0),
                'engine_struct_corr': correlation_data.get('engine-structural', 0)
            })
        
        # Temporal features
        self._update_history(features)
        if len(self.feature_history) >= self.window_size:
            features.update(self._get_temporal_features())
        
        # Ensure all features exist and are in consistent order
        return {name: features[name] for name in self.feature_names}
    
    def _ensure_anomaly_dict(self, anomalies):
        """Convert AnomalyScore objects to dict if needed"""
        if isinstance(anomalies, dict):
            return anomalies
        return {
            'rpm': anomalies.rpm if hasattr(anomalies, 'rpm') else AnomalyScore(False, 0, 0),
            'oil_pressure': anomalies.oil_pressure if hasattr(anomalies, 'oil_pressure') else AnomalyScore(False, 0, 0)
        }
    
    def _update_history(self, features: dict):
        """Maintain feature history"""
        self.feature_history.append(features)
        if len(self.feature_history) > self.window_size:
            self.feature_history.pop(0)
    
    def _get_temporal_features(self) -> dict:
        """Calculate features over time window"""
        rpm_values = [f['rpm_value'] for f in self.feature_history]
        vib_values = [f['vibration_value'] for f in self.feature_history]
        
        return {
            'rpm_trend': np.polyfit(range(len(rpm_values)), rpm_values, 1)[0],
            'vibration_increase': vib_values[-1] - vib_values[0],
            'anomaly_persistence': sum(
                1 for f in self.feature_history 
                if f['rpm_anomaly'] > 0.5 or f['oil_anomaly'] > 0.5
            ) / len(self.feature_history)
        }