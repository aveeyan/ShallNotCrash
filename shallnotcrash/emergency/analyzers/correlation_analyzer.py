#!/usr/bin/env python3
"""
Enhanced Cross-System Correlation Analysis for Cessna 172P
Integrated with emergency protocols and operational limits
"""
from dataclasses import dataclass
from enum import IntEnum
from typing import Dict, List, Tuple, Optional, Deque, DefaultDict
from collections import deque, defaultdict
import numpy as np
from scipy.stats import pearsonr
import time
from .. import constants

class CorrelationLevel(IntEnum):
    """Correlation severity levels aligned with emergency protocols"""
    NONE = 0
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    CRITICAL = 4

@dataclass
class CorrelationDiagnostic:
    """Enhanced correlation analysis result container"""
    level: CorrelationLevel
    confidence: float
    correlated_systems: Dict[str, float]  # system1-system2: score
    correlated_params: List[Tuple[str, str, float]]  # param1, param2, score
    recommendations: List[str]
    dominant_system: Optional[str] = None
    status_message: str = "Normal system correlations"
    structural_integrity: Optional[float] = None  # Added for structural monitoring

class CorrelationAnalyzer:
    """C172P-specific correlation analysis with structural monitoring"""
    
    def __init__(self, history_size: int = constants.DetectionParameters.CORRELATION_WINDOWS['long_term']):
        self.SYSTEM_WEIGHTS = {
            "engine": constants.SystemWeights.ENGINE,
            "fuel": constants.SystemWeights.FUEL,
            "structural": constants.SystemWeights.STRUCTURAL
        }
        
        self.CORRELATION_THRESHOLDS = {
            CorrelationLevel.CRITICAL: 0.85,
            CorrelationLevel.STRONG: 0.70,
            CorrelationLevel.MODERATE: 0.55,
            CorrelationLevel.WEAK: 0.40,
            CorrelationLevel.NONE: 0.0
        }
        
        # Structural monitoring parameters
        self.STRUCTURAL_PARAMS = [
            'vibration',
            'control_asymmetry',
            'g_load',
            'structural_integrity'
        ]
        
        self.history = deque(maxlen=history_size)
        self.system_severity = {
            system: deque(maxlen=history_size)
            for system in self.SYSTEM_WEIGHTS.keys()
        }
    
    def update_systems(self,
                     engine_status: Dict,
                     fuel_status: Dict,
                     structural_status: Dict):
        """Update system states with C172P-specific diagnostics"""
        self.history.append({
            'engine': engine_status,
            'fuel': fuel_status,
            'structural': structural_status
        })
        
        # Track system severities using anomaly scores
        self.system_severity['engine'].append(
            max(s.severity.value for s in engine_status.values()) 
            if engine_status else 0
        )
        self.system_severity['fuel'].append(
            max(s.severity.value for s in fuel_status.values())
            if fuel_status else 0
        )
        self.system_severity['structural'].append(
            self._calculate_structural_severity(structural_status)
        )
    
    def _calculate_structural_severity(self, status: Dict) -> float:
        """Compute composite structural severity score"""
        if not status:
            return 0.0
            
        weights = {
            'vibration': 0.4,
            'control_asymmetry': 0.3,
            'g_load': 0.2,
            'structural_integrity': 0.1
        }
        
        score = 0.0
        for param, weight in weights.items():
            if param in status:
                score += weight * status[param].severity.value
        return min(4.0, score)  # Cap at EMERGENCY level
    
    def analyze(self) -> CorrelationDiagnostic:
        """Perform complete C172P correlation analysis"""
        if len(self.history) < 10:  # Minimum samples
            return self._empty_diagnostic("Insufficient data for analysis")
        
        # System-level correlations
        system_correlations = self._calculate_system_correlations()
        
        # Parameter-level correlations
        param_correlations = self._calculate_parameter_correlations()
        
        # Structural integrity assessment
        structural_integrity = self._assess_structural_integrity()
        
        # Overall assessment
        overall_level, confidence = self._determine_overall_level(
            system_correlations, param_correlations)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            system_correlations, param_correlations)
        
        # Identify dominant system
        dominant_system = self._identify_dominant_system(system_correlations)
        
        return CorrelationDiagnostic(
            level=overall_level,
            confidence=confidence,
            correlated_systems=system_correlations,
            correlated_params=param_correlations,
            recommendations=recommendations,
            dominant_system=dominant_system,
            structural_integrity=structural_integrity,
            status_message=self._get_status_message(overall_level, dominant_system)
        )
    
    def _calculate_system_correlations(self) -> Dict[str, float]:
        """Calculate weighted correlations between system severities"""
        correlations = {}
        systems = list(self.SYSTEM_WEIGHTS.keys())
        
        severity_data = {
            sys: list(self.system_severity[sys])
            for sys in systems
        }
        
        for i, sys1 in enumerate(systems):
            for sys2 in systems[i+1:]:
                series1 = severity_data[sys1]
                series2 = severity_data[sys2]
                
                min_length = min(len(series1), len(series2))
                if min_length < 5:
                    correlations[f"{sys1}-{sys2}"] = 0.0
                    continue
                
                try:
                    corr, _ = pearsonr(series1[:min_length], series2[:min_length])
                    # Apply system weights to correlation score
                    weighted_corr = corr * (self.SYSTEM_WEIGHTS[sys1] + self.SYSTEM_WEIGHTS[sys2])/2
                    correlations[f"{sys1}-{sys2}"] = max(0, weighted_corr)
                except:
                    correlations[f"{sys1}-{sys2}"] = 0.0
        
        return correlations
    
    def _calculate_parameter_correlations(self) -> List[Tuple[str, str, float]]:
        """Calculate C172P-specific parameter correlations"""
        results = []
        
        # Engine parameters
        engine_pairs = [
            ('rpm', 'vibration'),
            ('oil_pressure', 'oil_temp'),
            ('cht', 'egt')
        ]
        
        # Structural parameters
        structural_pairs = [
            ('control_asymmetry', 'aileron'),
            ('g_load', 'elevator'),
            ('vibration', 'structural_integrity')
        ]
        
        for param1, param2 in engine_pairs + structural_pairs:
            vals1, vals2 = [], []
            
            for entry in self.history:
                val1 = (entry['engine'].get(param1) or 
                       entry['structural'].get(param1))
                val2 = (entry['engine'].get(param2) or
                       entry['structural'].get(param2))
                
                if val1 is not None and val2 is not None:
                    vals1.append(float(val1.value))
                    vals2.append(float(val2.value))
            
            if len(vals1) >= 5:
                try:
                    corr, _ = pearsonr(vals1, vals2)
                    results.append((param1, param2, max(0, corr)))
                except:
                    results.append((param1, param2, 0.0))
        
        return sorted(results, key=lambda x: x[2], reverse=True)
    
    def _assess_structural_integrity(self) -> Optional[float]:
        """Compute composite structural integrity score"""
        if not any(p in self.STRUCTURAL_PARAMS for entry in self.history 
                  for p in entry['structural'].keys()):
            return None
            
        scores = []
        for entry in self.history:
            struct = entry['structural']
            if not struct:
                continue
                
            score = 0.0
            count = 0
            for param in self.STRUCTURAL_PARAMS:
                if param in struct:
                    severity = struct[param].severity.value
                    score += (4 - severity) / 4  # Invert severity to integrity
                    count += 1
            if count > 0:
                scores.append(score / count)
                
        return np.mean(scores) if scores else None
    
    def _determine_overall_level(self,
                               system_correlations: Dict[str, float],
                               param_correlations: List[Tuple[str, str, float]]) -> Tuple[CorrelationLevel, float]:
        """Determine level using C172P-specific thresholds"""
        if not system_correlations or not param_correlations:
            return (CorrelationLevel.NONE, 0.0)
        
        # Weighted average of system correlations
        system_score = np.mean([
            corr * (self.SYSTEM_WEIGHTS[sys1] + self.SYSTEM_WEIGHTS[sys2])/2
            for systems, corr in system_correlations.items()
            for sys1, sys2 in [systems.split('-')]
        ]) if system_correlations else 0.0
        
        # Average of parameter correlations
        param_score = np.mean([corr for *_, corr in param_correlations]) if param_correlations else 0.0
        
        # Composite score with protocol weights
        composite_score = 0.6 * system_score + 0.4 * param_score
        
        # Determine level using protocol thresholds
        for level, threshold in sorted(self.CORRELATION_THRESHOLDS.items(), reverse=True):
            if composite_score >= threshold:
                return (level, composite_score)
        
        return (CorrelationLevel.NONE, composite_score)
    
    def _generate_recommendations(self,
                                system_correlations: Dict[str, float],
                                param_correlations: List[Tuple[str, str, float]]) -> List[str]:
        """Generate C172P-specific recommendations"""
        recommendations = []
        
        # System-level recommendations
        for systems, corr in system_correlations.items():
            if corr >= self.CORRELATION_THRESHOLDS[CorrelationLevel.STRONG]:
                sys1, sys2 = systems.split('-')
                rec = (
                    f"INSPECT: Strong correlation ({corr:.2f}) between "
                    f"{sys1.upper()} and {sys2.upper()} systems"
                )
                recommendations.append(rec)
        
        # Parameter-level recommendations
        for param1, param2, corr in param_correlations:
            if corr >= self.CORRELATION_THRESHOLDS[CorrelationLevel.STRONG]:
                rec = (
                    f"CHECK: High correlation ({corr:.2f}) between "
                    f"{param1.upper()} and {param2.upper()}"
                )
                recommendations.append(rec)
        
        return recommendations or ["No significant correlations detected"]
    
    def _identify_dominant_system(self, system_correlations: Dict[str, float]) -> Optional[str]:
        """Identify most correlated system with C172P weights"""
        if not system_correlations:
            return None
        
        system_scores = defaultdict(float)
        for systems, corr in system_correlations.items():
            sys1, sys2 = systems.split('-')
            weight = (self.SYSTEM_WEIGHTS[sys1] + self.SYSTEM_WEIGHTS[sys2])/2
            system_scores[sys1] += corr * weight
            system_scores[sys2] += corr * weight
        
        return max(system_scores.items(), key=lambda x: x[1])[0] if system_scores else None
    
    def _get_status_message(self, level: CorrelationLevel, dominant_system: Optional[str]) -> str:
        """Generate C172P-specific status messages"""
        messages = {
            CorrelationLevel.CRITICAL: (
                f"CRITICAL CORRELATION in {dominant_system.upper()} system! "
                "Immediate inspection required"
            ),
            CorrelationLevel.STRONG: (
                f"Strong correlations detected in {dominant_system.upper()} "
                "system - monitor closely"
            ),
            CorrelationLevel.MODERATE: "Moderate system correlations present",
            CorrelationLevel.WEAK: "Minor correlations observed",
            CorrelationLevel.NONE: "Normal system correlations"
        }
        return messages.get(level, "Correlation status unknown")
    
    def _empty_diagnostic(self, message: str = "Insufficient data") -> CorrelationDiagnostic:
        """Return empty diagnostic with status message"""
        return CorrelationDiagnostic(
            level=CorrelationLevel.NONE,
            confidence=0.0,
            correlated_systems={},
            correlated_params=[],
            recommendations=[message],
            dominant_system=None,
            status_message=message
        )

# Singleton instance with C172P configuration
CORRELATION_ANALYZER = CorrelationAnalyzer()

def analyze_system_correlations(engine_status: Dict,
                              fuel_status: Dict,
                              structural_status: Dict) -> CorrelationDiagnostic:
    """Public interface for C172P correlation analysis"""
    CORRELATION_ANALYZER.update_systems(engine_status, fuel_status, structural_status)
    return CORRELATION_ANALYZER.analyze()