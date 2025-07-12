#!/usr/bin/env python3
"""
Pattern Analyzer - Updated for type safety
"""
from .pr1_pattern_types import (
    EmergencyPattern,
    PatternResult,
    PatternConfidence,
    EMERGENCY_SIGNATURES
)
from typing import Dict, List, Optional

class PatternAnalyzer:
    def analyze(self, 
               ml_prediction: dict,
               features: dict) -> PatternResult:
        """Generate final pattern result"""
        
        # Get contributing features
        contributing = [
            f"{k}={v:.2f}" for k, v in features.items()
            if v > EMERGENCY_SIGNATURES[ml_prediction['pattern']]['thresholds'].get(k, 0)
        ]
        
        # Calculate time to critical
        ttc = self._estimate_time_to_critical(
            ml_prediction['pattern'],
            ml_prediction['probability'],
            features
        )
        
        return PatternResult(
            pattern_type=ml_prediction['pattern'],
            confidence=ml_prediction['confidence'],
            probability=ml_prediction['probability'],
            contributing_features=contributing,
            time_to_critical=ttc,
            recommended_action=ml_prediction['recommended_action'],
            anomaly_score=max(features.get('rpm_anomaly', 0), features.get('oil_anomaly', 0))
        )
    
    def _estimate_time_to_critical(self, 
                                 pattern: EmergencyPattern,
                                 probability: float,
                                 features: dict) -> Optional[float]:
        """Estimate time until critical state"""
        if pattern == EmergencyPattern.NORMAL:
            return None
            
        # Base estimates (seconds)
        base_times = {
            EmergencyPattern.ENGINE_DEGRADATION: 300,
            EmergencyPattern.FUEL_LEAK: 600,
            EmergencyPattern.STRUCTURAL_FATIGUE: 120
        }
        
        base_time = base_times.get(pattern, 300)
        return base_time * (1 - probability)  # Higher probability → less time