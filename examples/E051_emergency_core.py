#!/usr/bin/env python3
"""
Enhanced Emergency Detection Example
"""
import time
from pathlib import Path
import sys
from collections import deque
from typing import Dict, Any, Optional

sys.path.append(str(Path(__file__).parent.parent))
import time
from pprint import pprint
from shallnotcrash.emergency import core

def simulate_telemetry():
    """Generate realistic telemetry samples"""
    samples = [
        {'rpm': 2185, 'oil_pressure': 29, 'vibration': 1.22, 'cht': 308, 'fuel_flow': 15.1, 'altitude': 4650},
        {'rpm': 2450, 'oil_pressure': 32, 'vibration': 0.95, 'cht': 295, 'fuel_flow': 14.8, 'altitude': 4800},
        {'rpm': 1950, 'oil_pressure': 25, 'vibration': 2.15, 'cht': 335, 'fuel_flow': 17.3, 'altitude': 4500}
    ]
    for sample in samples:
        yield sample

def run_detection_example():
    """Run through detection scenarios"""
    anomalies = {
        'rpm': (True, 0.68, 'moderate'),
        'oil_pressure': (False, 0.15, 'minor')
    }
    
    correlations = {
        'engine-fuel': 0.45,
        'engine-structural': 0.37
    }
    
    print("Starting emergency detection simulation...\n")
    
    for i, telemetry in enumerate(simulate_telemetry()):
        print(f"\n=== Sample {i+1} ===")
        print("Telemetry:", {k: round(v,2) for k,v in telemetry.items()})
        
        result = core.detect_emergency_from_telemetry(
            telemetry=telemetry,
            anomaly_inputs=anomalies,
            correlation_data=correlations
        )
        
        print("\nDetection Result:")
        print(f"- Pattern: {result['pattern_type'].name}")
        print(f"- Confidence: {result['confidence'].name} ({result['probability']:.1%})")
        print(f"- Action: {result['recommended_action']}")
        print(f"- Time to Critical: {result['time_to_critical'] or 'N/A'} sec")
        print(f"- Trend: {'↑' if result['severity_trend'] > 0 else '↓'} {abs(result['severity_trend']):.2f}")
        
        # Update anomalies for next sample
        anomalies['rpm'] = (True, min(1.0, anomalies['rpm'][1] + 0.1), 'moderate')
        time.sleep(1)

if __name__ == "__main__":
    run_detection_example()