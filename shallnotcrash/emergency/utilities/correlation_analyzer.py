#!/usr/bin/env python3
## TODO: Fix the issue for correlation not working
"""
Cross-System Correlation Analysis
Identifies relationships between engine, fuel, and structural systems
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple
import numpy as np
from scipy.stats import pearsonr

class CorrelationLevel(Enum):
    NONE = 0
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    CRITICAL = 4

@dataclass
class CorrelationDiagnostic:
    """Cross-system correlation diagnosis"""
    level: CorrelationLevel
    confidence: float
    correlated_systems: Dict[str, float]
    correlated_params: List[Tuple[str, str, float]]
    recommendations: List[str]

class CorrelationAnalyzer:
    """Advanced correlation analysis for aviation systems"""
    SYSTEM_WEIGHTS = {
        "engine_failure": 0.40,
        "fuel_emergency": 0.35,
        "structural_failure": 0.25
    }
    
    PARAMETER_CORRELATIONS = [
        ('vibration', 'rpm', 0.8),
        ('g_load', 'oil_pressure', 0.7),
        ('fuel_flow', 'rpm', 0.9),
        ('control_asymmetry', 'oil_pressure', 0.6),
        ('total_fuel', 'endurance', 0.95),
        ('cht', 'oil_temp', 0.75),
        ('egt', 'fuel_flow', 0.85),
        ('vibration', 'g_load', 0.8),
        ('control_asymmetry', 'aileron', 0.7)
    ]
    
    def __init__(self):
        self.history = []
        self.history_size = 60  # 60 samples (1 minute at 1Hz)
        
    def analyze(self, engine_status: Dict, fuel_status: Dict, 
               structural_status: Dict) -> CorrelationDiagnostic:
        """Perform cross-system correlation analysis with historical data"""
        # Store current diagnostics in history
        self.history.append({
            'engine': engine_status.diagnostics,
            'fuel': fuel_status.diagnostics,
            'structural': structural_status.diagnostics
        })
        if len(self.history) > self.history_size:
            self.history.pop(0)
            
        # Calculate system-level correlation
        system_scores = {
            "engine": self._calculate_system_score(engine_status),
            "fuel": self._calculate_system_score(fuel_status),
            "structural": self._calculate_system_score(structural_status)
        }
        
        # Calculate pairwise system correlations
        system_correlations = {}
        systems = list(system_scores.keys())
        for i in range(len(systems)):
            for j in range(i+1, len(systems)):
                sys1, sys2 = systems[i], systems[j]
                correlation = self._normalized_correlation(
                    system_scores[sys1], system_scores[sys2])
                system_correlations[f"{sys1}-{sys2}"] = correlation
        
        # Calculate parameter-level correlations using historical data
        param_correlations = self._calculate_parameter_correlations()
        
        # Determine overall correlation level
        overall_score = np.mean(list(system_correlations.values()))
        corr_level, confidence = self._determine_correlation_level(overall_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(system_correlations)
        
        return CorrelationDiagnostic(
            level=corr_level,
            confidence=confidence,
            correlated_systems=system_correlations,
            correlated_params=param_correlations,
            recommendations=recommendations
        )
    
    def _calculate_system_score(self, diagnostic) -> float:
        """Calculate anomaly score for a system diagnostic"""
        if hasattr(diagnostic, 'severity'):
            return diagnostic.severity.value * 0.25
        elif isinstance(diagnostic, dict) and "severity" in diagnostic:
            return diagnostic["severity"].value * 0.25
        return 0.0

    def _calculate_parameter_correlations(self) -> List[Tuple]:
        """Calculate parameter correlations using historical data"""
        results = []
        for param1, param2, weight in self.PARAMETER_CORRELATIONS:
            # Extract time series from history
            vals1 = []
            vals2 = []
            for entry in self.history:
                # Extract values from diagnostics
                val1 = self._extract_value(entry, param1)
                val2 = self._extract_value(entry, param2)
                
                if val1 is not None and val2 is not None:
                    vals1.append(val1)
                    vals2.append(val2)
            
            # Only calculate if we have sufficient data
            if len(vals1) > 10:
                try:
                    corr = abs(pearsonr(vals1, vals2)[0])
                    results.append((param1, param2, corr * weight))
                except Exception:
                    results.append((param1, param2, 0.0))
        return results
    
    def _extract_value(self, entry: Dict, param: str) -> float:
        """Extract value from diagnostics entry"""
        for system in ['engine', 'fuel', 'structural']:
            if param in entry[system]:
                value = entry[system][param]
                if hasattr(value, 'value'):
                    return value.value
                return value
        return None
    
    def _determine_correlation_level(self, score: float) -> Tuple[CorrelationLevel, float]:
        """Map score to correlation level"""
        if score > 0.8: return CorrelationLevel.CRITICAL, score
        if score > 0.6: return CorrelationLevel.STRONG, score
        if score > 0.4: return CorrelationLevel.MODERATE, score
        if score > 0.2: return CorrelationLevel.WEAK, score
        return CorrelationLevel.NONE, 0.0
    
    def _generate_recommendations(self, system_correlations: Dict) -> List[str]:
        """Generate operational recommendations"""
        recommendations = []
        if system_correlations.get("engine-structural", 0) > 0.7:
            recommendations.append("Check engine mounts for structural stress")
        if system_correlations.get("engine-fuel", 0) > 0.6:
            recommendations.append("Monitor fuel system for engine-related anomalies")
        return recommendations
    
    def _normalized_correlation(self, a: float, b: float) -> float:
        """Calculate normalized correlation score"""
        return min(1.0, abs(a - b) * 2)

# Singleton instance
CORRELATION_ANALYZER = CorrelationAnalyzer()

def analyze_system_correlations(engine_status: Dict, fuel_status: Dict, 
                               structural_status: Dict) -> CorrelationDiagnostic:
    """Perform cross-system correlation analysis"""
    return CORRELATION_ANALYZER.analyze(engine_status, fuel_status, structural_status)
