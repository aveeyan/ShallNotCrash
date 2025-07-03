#!/usr/bin/env python3
"""
Emergency Detection Core System
Integrates protocol detectors with real-time correlation analysis
"""
import time
from typing import Dict, Any, List
from dataclasses import dataclass
from ..constants.flightgear import FGProps
from .protocols import (
    detect_engine_failure, 
    detect_fuel_emergency,
    detect_structural_failure,
)
from .utilities import (
    analyze_system_correlations,
    CorrelationLevel
)
from .constants import (
    EmergencySeverity, EmergencyConfig, EmergencyProcedures, EngineThresholds
)
from ..airplane.constants import C172PConstants

@dataclass
class Emergency:
    """Container for emergency state data"""
    severity: EmergencySeverity
    message: str
    checklist: List[str]
    timestamp: float
    confidence: float = 0.0
    is_active: bool = True

class EmergencyDetector:
    """Integrated emergency detection system with real-time correlation"""
    def __init__(self, fg_connection):
        """
        Args:
            fg_connection: Connected FGInterface instance
        """
        self.fg = fg_connection
        self._last_update = 0.0
        self._active_emergencies: Dict[str, Emergency] = {}
        self._system_diagnostics = {
            'engine': None,
            'fuel': None,
            'structural': None
        }

    def update(self) -> Dict[str, Emergency]:
        """Run all emergency checks and return active emergencies"""
        current_time = time.time()
        if current_time - self._last_update < 1/EmergencyConfig.TELEMETRY_RATE:
            return self._active_emergencies

        telemetry = self._get_telemetry()
        self._last_update = current_time

        # Phase 1: System detection using protocol detectors
        self._update_system_diagnostics(telemetry)
        
        # Phase 2: Cross-system correlation analysis
        self._process_correlations()
        
        # Phase 3: Time-based validation
        self._validate_emergencies()

        return {k: v for k, v in self._active_emergencies.items() if v.is_active}
    
    def _update_system_diagnostics(self, telemetry: Dict[str, float]):
        """Update diagnostics from all protocol detectors"""
        self._system_diagnostics['engine'] = detect_engine_failure(telemetry)
        self._system_diagnostics['fuel'] = detect_fuel_emergency(telemetry)
        self._system_diagnostics['structural'] = detect_structural_failure(telemetry)
        
        # Register system-specific emergencies
        self._register_system_emergency('engine', 'ENGINE_FAILURE', "Engine failure detected")
        self._register_system_emergency('fuel', 'FUEL_EMERGENCY', "Fuel emergency detected")
        self._register_system_emergency('structural', 'STRUCTURAL_FAILURE', "Structural failure detected")

    def _register_system_emergency(self, system: str, name: str, message: str):
        """Register emergency for a specific system if detected"""
        diagnostic = self._system_diagnostics[system]
        
        # Check if system has detected an emergency
        if getattr(diagnostic, 'is_failure', False) or getattr(diagnostic, 'is_emergency', False):
            self._register_emergency(
                name,
                Emergency(
                    severity=diagnostic.severity,
                    message=f"{message} (Confidence: {diagnostic.confidence:.0%})",
                    checklist=self._generate_checklist(system),
                    confidence=diagnostic.confidence,
                    timestamp=time.time()
                )
            )

    def _generate_checklist(self, system: str) -> List[str]:
        """Generate emergency checklist for specific system"""
        if system == 'engine':
            return [
                f"Pitch for {C172PConstants.EMERGENCY['GLIDE_SPEED']} KIAS",
                f"Expected descent: {C172PConstants.EMERGENCY['ENGINE_OUT_CLIMB_RATE']} ft/min",
                f"Max restart attempts: {EngineThresholds.RESTART['MAX_ATTEMPTS']}",
                f"Restart within {EngineThresholds.RESTART['ATTEMPT_INTERVAL']} sec intervals"
            ]
        elif system == 'fuel':
            return [
                f"Switch to fullest tank",
                f"Fuel pump: ON",
                f"Land within {C172PConstants.EMERGENCY['MIN_GLIDE_RANGE']} NM",
                f"Target speed: {C172PConstants.EMERGENCY['GLIDE_SPEED']} KIAS"
            ]
        else:  # structural
            return [
                "Reduce airspeed to V<sub>FE</sub>",
                "Avoid abrupt maneuvers",
                "Secure loose items",
                "Prepare for emergency landing"
            ]

    def _process_correlations(self):
        """Perform and process cross-system correlation analysis"""
        # Get diagnostics from all systems
        engine_diag = self._system_diagnostics['engine']
        fuel_diag = self._system_diagnostics['fuel']
        structural_diag = self._system_diagnostics['structural']
        
        # Perform correlation analysis
        correlation_diag = analyze_system_correlations(
            engine_diag.diagnostics,
            fuel_diag.diagnostics,
            structural_diag.diagnostics
        )
        
        # Register if correlation indicates emergency
        if correlation_diag.emergency_level != CorrelationLevel.NONE:
            self._register_emergency(
                'CROSS_SYSTEM_CORRELATION',
                Emergency(
                    severity=EmergencySeverity.CRITICAL,
                    message="Critical system correlation detected",
                    checklist=correlation_diag.recommendations,
                    confidence=correlation_diag.confidence,
                    timestamp=time.time()
                )
            )

    def _get_telemetry(self) -> Dict[str, Any]:
        """Fetch critical telemetry with error handling"""
        try:
            return {
                # Engine systems
                'rpm': self.fg.get(FGProps.ENGINE.RPM)['data']['value'],
                'cht': self.fg.get(FGProps.ENGINE.CHT_F)['data']['value'],
                'oil_temp': self.fg.get(FGProps.ENGINE.OIL_TEMP_F)['data']['value'],
                'oil_press': self.fg.get(FGProps.ENGINE.OIL_PRESS_PSI)['data']['value'],
                'fuel_flow': self.fg.get(FGProps.ENGINE.FUEL_FLOW_GPH)['data']['value'],
                'vibration': self.fg.get(FGProps.ENGINE.VIBRATION)['data']['value'],
                
                # Fuel system
                'fuel_left': self.fg.get(FGProps.FUEL.LEFT_QTY_GAL)['data']['value'],
                'fuel_right': self.fg.get(FGProps.FUEL.RIGHT_QTY_GAL)['data']['value'],
                
                # Flight state
                'airspeed': self.fg.get(FGProps.FLIGHT.AIRSPEED_KT)['data']['value'],
                'altitude': self.fg.get(FGProps.FLIGHT.ALTITUDE_FT)['data']['value'],
                'vsi': self.fg.get(FGProps.FLIGHT.VERTICAL_SPEED_FPS)['data']['value'] * 60,
                'g_load': self._calculate_g_load(),
                
                # Control surfaces
                'aileron': self.fg.get(FGProps.CONTROLS.AILERON)['data']['value'],
                'elevator': self.fg.get(FGProps.CONTROLS.ELEVATOR)['data']['value'],
                'rudder': self.fg.get(FGProps.CONTROLS.RUDDER)['data']['value'],
            }
        except Exception as e:
            print(f"Telemetry error: {str(e)}")
            return {}

    def _calculate_g_load(self) -> float:
        """Calculate approximate G-load from vertical acceleration"""
        try:
            accel_z = self.fg.get(FGProps.FLIGHT.ACCEL_Z)['data']['value']
            return abs(accel_z) / 32.2 + 1.0  # Convert to Gs
        except:
            return 1.0  # Default to 1G if unavailable

    def _register_emergency(self, name: str, emergency: Emergency):
        """Manage emergency state with debouncing"""
        current_time = time.time()
        debounce_time = EmergencyConfig.DEBOUNCE_TIME.get(emergency.severity, 1.0)
        
        if name in self._active_emergencies:
            if current_time - self._active_emergencies[name].timestamp > debounce_time:
                self._active_emergencies[name] = emergency
            else:
                # Update timestamp but keep existing emergency
                self._active_emergencies[name].timestamp = current_time
        else:
            self._active_emergencies[name] = emergency

    def _validate_emergencies(self):
        """Remove expired emergencies using configured persistence"""
        current_time = time.time()
        min_alert_duration = EmergencyConfig.MIN_ALERT_DURATION
        
        for name, emergency in list(self._active_emergencies.items()):
            if current_time - emergency.timestamp > min_alert_duration:
                del self._active_emergencies[name]
    