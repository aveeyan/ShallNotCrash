#!/usr/bin/env python3
"""
Main System - Updated Integration
"""
from pr1_pattern_types import TelemetryData, AnomalyScore
from pr2_feature_extractor import FeatureExtractor
from pr3_ml_models import MLModelManager
from pr4_pattern_analyzer import PatternAnalyzer, PatternResult

from typing import Dict

class PatternRecognizer:
    def __init__(self, model_path: str):
        self.features = FeatureExtractor()
        self.ml = MLModelManager()
        self.analyzer = PatternAnalyzer()
        self.ml.load(model_path)
    
    def process(self,
               telemetry: TelemetryData,
               anomalies: Dict[str, AnomalyScore]) -> PatternResult:
        # Extract features
        features = self.features.extract(telemetry, anomalies)
        
        # ML prediction
        ml_result = self.ml.predict(features)
        
        # Generate final result
        return self.analyzer.analyze(ml_result, features)

# Singleton instance
_recognizer = None

def get_recognizer(model_path="models/default_model.joblib"):
    global _recognizer
    if _recognizer is None:
        _recognizer = PatternRecognizer(model_path)
    return _recognizer