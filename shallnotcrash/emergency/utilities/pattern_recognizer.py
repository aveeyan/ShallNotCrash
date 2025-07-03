#!/usr/bin/env python3
"""
Pattern Recognition for Aviation Systems
Detects emergency patterns across flight systems
"""
from typing import Dict
from .anomaly_detector import AnomalyScore

class PatternRecognizer:
    def __init__(self):
        self.emergency_patterns = self._load_emergency_patterns()
    
    def _load_emergency_patterns(self) -> Dict[str, Dict]:
        """Define known emergency patterns with weights"""
        return {
            "ENGINE_DETACHMENT": {
                "vibration": (8.0, 0.9),
                "control_asymmetry": (2.5, 0.8),
                "g_load": (4.0, 0.7)
            },
            "WING_STRUCTURE_FAILURE": {
                "aileron": (0.8, 0.9),
                "vibration": (7.5, 0.85),
                "g_load": (3.8, 0.75)
            }
        }
    
    def predict(self, anomaly_scores: Dict[str, AnomalyScore]) -> Dict[str, float]:
        """Predict emergency probability using known patterns"""
        predictions = {}
        
        for pattern_name, pattern in self.emergency_patterns.items():
            score = 0.0
            total_weight = 0.0
            
            for param, (threshold, weight) in pattern.items():
                if param in anomaly_scores:
                    anomaly = anomaly_scores[param]
                    if anomaly.is_anomaly and anomaly.value > threshold:
                        score += weight
                    total_weight += weight
            
            if total_weight > 0:
                predictions[pattern_name] = score / total_weight
        
        return predictions

# Singleton instance
PATTERN_RECOGNIZER = PatternRecognizer()

def recognize_emergency_patterns(anomaly_scores: Dict[str, AnomalyScore]) -> Dict[str, float]:
    """Detect known emergency patterns"""
    return PATTERN_RECOGNIZER.predict(anomaly_scores)
