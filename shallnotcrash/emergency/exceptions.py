# shallnotcrash/emergency/exceptions.py
#!/usr/bin/env python3
"""
Emergency System Exceptions
Standardized error types for emergency detection and handling
"""

class EmergencyError(Exception):
    """Base class for all emergency system errors"""
    pass

class TelemetryError(EmergencyError):
    """Failed to read or process telemetry data"""
    def __init__(self, message="Telemetry system failure", component=None):
        self.component = component
        super().__init__(f"{message} [Component: {component}]" if component else message)

class ProtocolError(EmergencyError):
    """Failure in emergency protocol execution"""
    def __init__(self, protocol_name, message="Protocol failure"):
        self.protocol_name = protocol_name
        super().__init__(f"{message} in {protocol_name}")

class ThresholdError(EmergencyError):
    """Invalid threshold configuration detected"""
    def __init__(self, threshold_name, value, message="Invalid threshold value"):
        self.threshold_name = threshold_name
        self.value = value
        super().__init__(f"{message}: {threshold_name}={value}")

class ConfigurationError(EmergencyError):
    """Invalid system configuration detected"""
    def __init__(self, config_name, message="Configuration error"):
        self.config_name = config_name
        super().__init__(f"{message}: {config_name}")

class SensorFailure(EmergencyError):
    """Critical sensor malfunction detected"""
    def __init__(self, sensor_name, message="Sensor failure"):
        self.sensor_name = sensor_name
        super().__init__(f"{message}: {sensor_name}")

class EmergencyActivationError(EmergencyError):
    """Failed to activate emergency procedures"""
    def __init__(self, emergency_type, message="Emergency activation failed"):
        self.emergency_type = emergency_type
        super().__init__(f"{message} for {emergency_type}")

class ResponseError(EmergencyError):
    """Failure in emergency response execution"""
    def __init__(self, action, message="Response action failed"):
        self.action = action
        super().__init__(f"{message}: {action}")