#!/usr/bin/env python3
"""
Emergency detection core for Cessna 172P
Now with complete constant-driven operation
"""
import time
from typing import Dict, Any
from dataclasses import dataclass
from ..constants.flightgear import FGProps
from .constants import (
    EmergencySeverity,
    EngineThresholds,
    FuelThresholds,
    AerodynamicThresholds,
    FGEmergencyPaths,
    EmergencyConfig,
    ResponseTimes,
    EmergencyProcedures
)
from ..airplane.constants import C172PConstants

@dataclass
class Emergency:
    """Container for emergency state data"""
    severity: EmergencySeverity
    message: str
    checklist: list[str]
    timestamp: float
    is_active: bool = True

class EmergencyDetector:
    def __init__(self, fg_connection):
        """
        Args:
            fg_connection: Connected FGInterface instance
        """
        self.fg = fg_connection
        self._last_update = 0.0
        self._active_emergencies: Dict[str, Emergency] = {}
        self._restart_attempts = 0

    def update(self) -> Dict[str, Emergency]:
        """Run all emergency checks and return active emergencies"""
        current_time = time.time()
        if current_time - self._last_update < 1/EmergencyConfig.TELEMETRY_RATE:
            return self._active_emergencies

        telemetry = self._get_telemetry()
        self._last_update = current_time

        # Phase 1: System-specific threshold checks
        self._check_engine(telemetry)
        self._check_fuel(telemetry)
        self._check_aerodynamics(telemetry)
        self._check_electrical(telemetry)

        # Phase 2: Cross-system correlations
        self._check_compound_emergencies(telemetry)

        # Phase 3: Time-based validation
        self._validate_emergencies()

        return {k: v for k, v in self._active_emergencies.items() if v.is_active}

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
                
                # Fuel system
                'fuel_left': self.fg.get(FGProps.FUEL.LEFT_QTY_GAL)['data']['value'],
                'fuel_right': self.fg.get(FGProps.FUEL.RIGHT_QTY_GAL)['data']['value'],
                
                # Flight state
                'airspeed': self.fg.get(FGProps.FLIGHT.AIRSPEED_KT)['data']['value'],
                'altitude': self.fg.get(FGProps.FLIGHT.ALTITUDE_FT)['data']['value'],
                'vsi': self.fg.get(FGProps.FLIGHT.VERTICAL_SPEED_FPS)['data']['value'] * 60,
                'glide_ratio': self._calculate_glide_ratio(),
                
                # Environmental
                'oat': self.fg.get(FGEmergencyPaths.OAT_C)['data']['value'],
                'humidity': self.fg.get(FGEmergencyPaths.HUMIDITY)['data']['value'],
                
                # System states
                'carb_heat': self.fg.get(FGEmergencyPaths.CARB_HEAT)['data']['value'],
                'fuel_selector': self.fg.get(FGEmergencyPaths.FUEL_SELECTOR)['data']['value'],
                
                # Electrical
                'bus_voltage': self.fg.get(FGProps.ELECTRICAL.BUS_VOLTS)['data']['value'],
                'alternator_output': self.fg.get(FGProps.ELECTRICAL.ALTERNATOR_AMPS)['data']['value']
            }
        except Exception as e:
            print(f"Telemetry error: {str(e)}")
            return {}

    def _calculate_glide_ratio(self) -> float:
        """Calculate current glide ratio based on performance"""
        # Base glide ratio adjusted for current conditions
        return C172PConstants.EMERGENCY['GLIDE_RATIO'] * 0.9  # Conservative estimate

    def _check_engine(self, telemetry: Dict[str, Any]):
        """Enhanced engine system checks"""
        if not telemetry:
            return

        # Engine failure
        if telemetry['rpm'] < C172PConstants.ENGINE['MIN_RUNNING_RPM']:
            checklist = [
                f"Pitch for {C172PConstants.EMERGENCY['GLIDE_SPEED']} KIAS",
                f"Expected descent: {C172PConstants.EMERGENCY['ENGINE_OUT_CLIMB_RATE']} ft/min",
                f"Glide ratio: {telemetry['glide_ratio']:.1f}:1",
                f"Max attempts: {EngineThresholds.RESTART['MAX_ATTEMPTS']}"
            ]
            
            if telemetry['altitude'] > C172PConstants.EMERGENCY['RESTART_MIN_ALT']:
                checklist.extend([
                    f"Attempt restart within {EngineThresholds.RESTART['ATTEMPT_INTERVAL']} sec",
                    f"Minimum restart altitude: {C172PConstants.EMERGENCY['RESTART_MIN_ALT']} ft"
                ])

            self._register_emergency(
                'ENGINE_FAILURE',
                Emergency(
                    severity=EmergencySeverity.EMERGENCY,
                    message=(f"ENGINE FAILURE! Alt: {telemetry['altitude']:.0f}ft | "
                            f"Glide range: {telemetry['altitude']/1000 * telemetry['glide_ratio']:.1f} NM"),
                    checklist=checklist,
                    timestamp=time.time()
                )
            )

        # Temperature warnings
        if telemetry['cht'] > EngineThresholds.CHT['CRITICAL']:
            self._register_emergency(
                'ENGINE_OVERHEAT',
                Emergency(
                    severity=EmergencySeverity.CRITICAL,
                    message=f"CHT CRITICAL: {telemetry['cht']:.0f}°F (Max {EngineThresholds.CHT['CRITICAL']}°F)",
                    checklist=[
                        f"Reduce power below {C172PConstants.ENGINE['REDLINE_RPM']} RPM",
                        f"Maintain >{C172PConstants.SPEEDS['VNO']} KIAS",
                        "Check cowl flaps"
                    ],
                    timestamp=time.time()
                )
            )

    def _check_fuel(self, telemetry: Dict[str, Any]):
        """Enhanced fuel system checks"""
        if not telemetry:
            return

        total_fuel = telemetry['fuel_left'] + telemetry['fuel_right']
        imbalance = abs(telemetry['fuel_left'] - telemetry['fuel_right'])

        # Critical fuel state
        if total_fuel < FuelThresholds.QTY['CRITICAL']:
            glide_range = telemetry['altitude']/1000 * telemetry['glide_ratio']
            self._register_emergency(
                'FUEL_CRITICAL',
                Emergency(
                    severity=EmergencySeverity.EMERGENCY,
                    message=f"FUEL EMERGENCY: {total_fuel:.1f}gal | Glide range: {glide_range:.1f}NM",
                    checklist=[
                        f"Land within {min(glide_range, total_fuel * 8):.1f} NM",
                        f"Target speed: {C172PConstants.EMERGENCY['GLIDE_SPEED']} KIAS",
                        f"Pattern altitude: {C172PConstants.EMERGENCY['PATTERN_ALTITUDE']}ft"
                    ],
                    timestamp=time.time()
                )
            )

        # Fuel imbalance
        if imbalance > FuelThresholds.IMBALANCE['CRITICAL']:
            self._register_emergency(
                'FUEL_IMBALANCE',
                Emergency(
                    severity=EmergencySeverity.WARNING,
                    message=f"Fuel imbalance: {imbalance:.1f}gal (Max {FuelThresholds.IMBALANCE['CRITICAL']}gal)",
                    checklist=[
                        "Fuel selector: BOTH",
                        f"Monitor every {EmergencyProcedures.ENGINE_FAILURE['ACTION_DELAYS']['FUEL_SELECTOR_CHANGE']} sec",
                        "Consider crossfeed if equipped"
                    ],
                    timestamp=time.time()
                )
            )

    def _check_electrical(self, telemetry: Dict[str, Any]):
        """New electrical system checks"""
        if not telemetry:
            return

        if telemetry['bus_voltage'] < C172PConstants.ELECTRICAL['MIN_BUS_VOLTAGE']:
            self._register_emergency(
                'ELECTRICAL_FAILURE',
                Emergency(
                    severity=EmergencySeverity.WARNING,
                    message=f"ELECTRICAL FAILURE: {telemetry['bus_voltage']:.1f}V (Min {C172PConstants.ELECTRICAL['MIN_BUS_VOLTAGE']}V)",
                    checklist=[
                        "Alternator: CHECK",
                        "Non-essential electronics: OFF",
                        f"Expected battery life: {self._calculate_battery_life(telemetry):.0f} min"
                    ],
                    timestamp=time.time()
                )
            )

    def _calculate_battery_life(self, telemetry: Dict[str, Any]) -> float:
        """Estimate remaining battery time"""
        load = 10  # Simplified assumption (amps)
        return (24 * 60) / load  # 24Ah battery

    def _check_fuel(self, telemetry: Dict[str, Any]):
        """Fuel system emergency checks"""
        if not telemetry:
            return

        total_fuel = telemetry['fuel_left'] + telemetry['fuel_right']
        imbalance = abs(telemetry['fuel_left'] - telemetry['fuel_right'])

        # Critical fuel state
        if total_fuel < FuelThresholds.QTY['CRITICAL']:
            self._register_emergency(
                'FUEL_CRITICAL',
                Emergency(
                    severity=EmergencySeverity.CRITICAL,
                    message=f"FUEL CRITICAL: {total_fuel:.1f} gal (Min {FuelThresholds.QTY['CRITICAL']} gal)",
                    checklist=[
                        "Fuel selector: BOTH",
                        "Mixture: RICH",
                        f"Land within {total_fuel * 8:.0f} NM"  # ~8 NM/gal at cruise
                    ],
                    timestamp=time.time()
                )
            )

        # Fuel imbalance
        if imbalance > FuelThresholds.IMBALANCE['CRITICAL']:
            self._register_emergency(
                'FUEL_IMBALANCE',
                Emergency(
                    severity=EmergencySeverity.WARNING,
                    message=f"Fuel imbalance: {imbalance:.1f} gal (Max {FuelThresholds.IMBALANCE['CRITICAL']} gal)",
                    checklist=[
                        "Fuel selector: BOTH",
                        "Monitor fuel flow",
                        "Consider crossfeed if equipped"
                    ],
                    timestamp=time.time()
                )
            )

    def _check_aerodynamics(self, telemetry: Dict[str, Any]):
        """Flight dynamics emergency checks"""
        if not telemetry:
            return

        # Stall detection
        stall_speed = C172PConstants.SPEEDS['VS0'] + AerodynamicThresholds.STALL['SPEED_BUFFER']
        if (telemetry['airspeed'] < stall_speed and
            telemetry['vsi'] < AerodynamicThresholds.STALL['VSI_CRITICAL']):
            self._register_emergency(
                'STALL',
                Emergency(
                    severity=EmergencySeverity.CRITICAL,
                    message=f"STALL WARNING: {telemetry['airspeed']:.1f} kt (Min {stall_speed} kt)",
                    checklist=[
                        "Pitch down immediately",
                        f"Apply full power ({C172PConstants.ENGINE['REDLINE_RPM']} RPM)",
                        "Level wings",
                        f"Retract flaps to 20° if >{C172PConstants.SPEEDS['VFE']} kt"
                    ],
                    timestamp=time.time()
                )
            )

    def _check_compound_emergencies(self, telemetry: Dict[str, Any]):
        """Check for emergencies requiring multiple system states"""
        if not telemetry:
            return

        # Carb icing
        if (telemetry['oat'] < EngineThresholds.CARB_ICE['OAT_MAX_RISK'] and 
            telemetry['humidity'] > EngineThresholds.CARB_ICE['HUMIDITY_MIN'] and
            telemetry['carb_heat'] == 0):
            self._register_emergency(
                'CARB_ICING',
                Emergency(
                    severity=EmergencySeverity.WARNING,
                    message=f"CARB ICING RISK: {telemetry['oat']:.1f}°C, {telemetry['humidity']:.0f}% RH",
                    checklist=[
                        "Carb heat: ON",
                        f"Monitor RPM (expect {EngineThresholds.CARB_ICE['RPM_DROP_WARNING']} drop)",
                        "Check EGT rise"
                    ],
                    timestamp=time.time()
                )
            )

    def _register_emergency(self, name: str, emergency: Emergency):
        """Manage emergency state with debouncing"""
        current_time = time.time()
        
        if name in self._active_emergencies:
            self._active_emergencies[name].timestamp = current_time
        else:
            self._active_emergencies[name] = emergency

    def _validate_emergencies(self):
        """Remove expired emergencies"""
        current_time = time.time()
        
        self._active_emergencies = {
            name: emergency 
            for name, emergency in self._active_emergencies.items()
            if current_time - emergency.timestamp < ResponseTimes.ALERT_DELAYS[emergency.severity]
        }
