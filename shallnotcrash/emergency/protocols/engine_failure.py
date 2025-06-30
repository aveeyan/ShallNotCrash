#!/usr/bin/env python3
"""
Engine Failure Emergency Protocol for Cessna 172P
Implements phased emergency response with dynamic state management
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

# Relative imports within shallnotcrash package
from ...constants.flightgear import FGProps
from ..constants import EmergencySeverity, EmergencyProcedures, EngineThresholds

class EngineFailureStage(Enum):
    IMMEDIATE_ACTIONS = auto()
    RESTART_ATTEMPT = auto()
    FORCED_LANDING_PREP = auto()
    FINAL_APPROACH = auto()

@dataclass
class ProtocolStage:
    name: str
    actions: List[str]
    conditions: Dict[str, Tuple[float, float]]
    severity: EmergencySeverity

class EngineFailureProtocol:
    """Stateful engine failure emergency protocol"""
    def __init__(self):
        self._restart_attempts = 0
        self._current_stage = EngineFailureStage.IMMEDIATE_ACTIONS
        self._max_restart_attempts = EmergencyProcedures.ENGINE_FAILURE['MAX_RESTART_ATTEMPTS']
        
        # Build emergency response stages
        self.stages = self._build_stages()
    
    def _build_stages(self) -> Dict[EngineFailureStage, ProtocolStage]:
        """Construct the engine failure response protocol"""
        # Use fallback if ENGINE_FAILURE_RPM isn't defined in EngineThresholds
        engine_failure_rpm = getattr(EngineThresholds, 'ENGINE_FAILURE_RPM', 200)
        
        return {
            EngineFailureStage.IMMEDIATE_ACTIONS: ProtocolStage(
                name="Immediate Actions",
                actions=[
                    "Establish best glide speed (67 KIAS)",
                    "Pitch for 67 KIAS, trim to maintain",
                    "Identify landing site within glide range",
                    "Carb heat ON (if equipped)",
                    "Fuel selector: BOTH",
                    "Mixture: RICH",
                    "Throttle: CHECK",
                    "Magnetos: CHECK BOTH→L→R→BOTH"
                ],
                conditions={
                    FGProps.ENGINE.RPM: (0, engine_failure_rpm)
                },
                severity=EmergencySeverity.EMERGENCY
            ),
            EngineFailureStage.RESTART_ATTEMPT: ProtocolStage(
                name="Restart Attempt",
                actions=[
                    "Fuel pump: ON",
                    "Throttle: 1/2 inch OPEN",
                    "Mixture: CYCLE (lean-rich-lean)",
                    f"Attempt restart (if altitude > {EmergencyProcedures.ENGINE_FAILURE['MIN_FINAL_ALT']} ft)"
                ],
                conditions={
                    FGProps.FLIGHT.ALTITUDE_FT: (EmergencyProcedures.ENGINE_FAILURE['MIN_FINAL_ALT'], 10000),
                    'restart_attempts': (0, self._max_restart_attempts)
                },
                severity=EmergencySeverity.CRITICAL
            ),
            EngineFailureStage.FORCED_LANDING_PREP: ProtocolStage(
                name="Forced Landing Preparation",
                actions=[
                    "Mayday call: declare emergency",
                    "Seatbelts: SECURE",
                    "Doors: UNLATCH",
                    "Flaps: AS REQUIRED (consider no-flap landing)",
                    "Master switch: OFF before touchdown",
                    "Fuel selector: OFF",
                    "Mixture: IDLE CUTOFF"
                ],
                conditions={
                    FGProps.FLIGHT.ALTITUDE_FT: (500, EmergencyProcedures.ENGINE_FAILURE['MIN_FINAL_ALT']),
                    'distance_to_target': (0, 3)  # NM
                },
                severity=EmergencySeverity.EMERGENCY
            ),
            EngineFailureStage.FINAL_APPROACH: ProtocolStage(
                name="Final Approach",
                actions=[
                    "Speed: 61 KIAS (add 1/2 gust factor)",
                    "Airspeed: MONITOR constantly",
                    "Spoilers: PREPARE (if equipped)",
                    "Touchdown: WHEELS FIRST (if tricycle)",
                    "Braking: MAXIMUM after touchdown"
                ],
                conditions={
                    FGProps.FLIGHT.ALTITUDE_FT: (0, 500),
                    FGProps.FLIGHT.AIRSPEED_KT: (55, 70)
                },
                severity=EmergencySeverity.CRITICAL
            )
        }
    
    def get_actions(self, telemetry: Dict[str, float]) -> List[str]:
        """Get current emergency checklist based on flight state"""
        self._update_stage(telemetry)
        return self.stages[self._current_stage].actions
    
    def _update_stage(self, telemetry: Dict[str, float]):
        """Transition between protocol stages based on conditions"""
        # Include protocol state in telemetry for condition evaluation
        eval_telemetry = {
            **telemetry,
            'restart_attempts': self._restart_attempts
        }
        
        # Check stage progression conditions
        if self._current_stage == EngineFailureStage.IMMEDIATE_ACTIONS:
            if self._check_conditions(
                self.stages[EngineFailureStage.RESTART_ATTEMPT].conditions,
                eval_telemetry
            ):
                self._current_stage = EngineFailureStage.RESTART_ATTEMPT
                
        elif self._current_stage == EngineFailureStage.RESTART_ATTEMPT:
            if self._check_conditions(
                self.stages[EngineFailureStage.FORCED_LANDING_PREP].conditions,
                eval_telemetry
            ):
                self._current_stage = EngineFailureStage.FORCED_LANDING_PREP
                
        elif self._current_stage == EngineFailureStage.FORCED_LANDING_PREP:
            if self._check_conditions(
                self.stages[EngineFailureStage.FINAL_APPROACH].conditions,
                eval_telemetry
            ):
                self._current_stage = EngineFailureStage.FINAL_APPROACH
    
    def _check_conditions(self,
                         conditions: Dict[str, Tuple[float, float]],
                         telemetry: Dict[str, float]) -> bool:
        """Verify if all conditions are satisfied"""
        for param, (min_val, max_val) in conditions.items():
            # Handle both FG property paths and custom parameters
            value = telemetry.get(param)
            if value is None:
                return False
            if not (min_val <= value <= max_val):
                return False
        return True
    
    def record_restart_attempt(self):
        """Log restart attempt and advance counter"""
        if self._restart_attempts < self._max_restart_attempts:
            self._restart_attempts += 1
    
    def reset(self):
        """Reset protocol state between flights"""
        self._restart_attempts = 0
        self._current_stage = EngineFailureStage.IMMEDIATE_ACTIONS

    def get_stage_name(self, telemetry: Dict[str, float]) -> str:
        """Get human-readable stage name"""
        self._update_stage(telemetry)
        return self.stages[self._current_stage].name

# Singleton instance for system-wide use
ENGINE_FAILURE_PROTOCOL = EngineFailureProtocol()

def get_current_stage(telemetry: Dict[str, float]) -> str:
    """Get current stage name for monitoring systems"""
    return ENGINE_FAILURE_PROTOCOL.get_stage_name(telemetry)

def get_restart_attempts() -> int:
    """Get current restart attempt count"""
    return ENGINE_FAILURE_PROTOCOL._restart_attempts

def reset_protocol():
    """Reset protocol state (for simulation/testing)"""
    ENGINE_FAILURE_PROTOCOL.reset()