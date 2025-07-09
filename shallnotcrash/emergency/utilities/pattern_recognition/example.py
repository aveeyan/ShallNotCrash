from main import get_recognizer
from pr1_pattern_types import TelemetryData, AnomalyScore

# Sample data
telemetry = TelemetryData(rpm=1500, oil_pressure=12.3)
anomalies = {
    'rpm': AnomalyScore(True, 0.85, 3),
    'oil_pressure': AnomalyScore(True, 0.92, 4)
}

# Process
recognizer = get_recognizer()
result = recognizer.process(telemetry, anomalies)

print(f"Detected: {result.pattern_type.name}")
print(f"Action: {result.recommended_action}")
print(f"Time to critical: {result.time_to_critical}s")