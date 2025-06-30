#!/usr/bin/env python3
"""
Engine Failure Emergency Protocol for Cessna 172P
Complete implementation with safe constant handling
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

# Default engine failure procedures
ENGINE_FAILURE_DEFAULTS = {
    'MAX_RESTART_ATTEMPTS': 3,
    'MIN_FINAL_ALT': 500,  # ft
    'MIN_RESTART_ALT': 2000  # ft
}

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
    severity: str

class EngineFailureProtocol:
    """Stateful engine failure emergency protocol"""
    def __init__(self):
        self._restart_attempts = 0
        self._current_stage = EngineFailureStage.IMMEDIATE_ACTIONS
        self.stages = self._build_stages()
    
    def _build_stages(self) -> Dict[EngineFailureStage, ProtocolStage]:
        """Construct engine failure response protocol"""
        # Safe constant access with fallbacks
        max_attempts = self._get_constant('MAX_RESTART_ATTEMPTS', 3)
        min_final_alt = self._get_constant('MIN_FINAL_ALT', 500)
        min_restart_alt = self._get_constant('MIN_RESTART_ALT', 2000)
        
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
                    'rpm': (0, 1000)  # Using safe value instead of undefined constant
                },
                severity="EMERGENCY"
            ),
            EngineFailureStage.RESTART_ATTEMPT: ProtocolStage(
                name="Restart Attempt",
                actions=[
                    "Fuel pump: ON",
                    "Throttle: 1/2 inch OPEN",
                    "Mixture: CYCLE (lean-rich-lean)",
                    f"Attempt restart (if altitude > {min_restart_alt} ft)"
                ],
                conditions={
                    'altitude': (min_final_alt, 10000),
                    'restart_attempts': (0, max_attempts)
                },
                severity="CRITICAL"
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
                    'altitude': (500, min_final_alt),
                    'distance_to_target': (0, 3)  # NM
                },
                severity="EMERGENCY"
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
                    'altitude': (0, 500),
                    'airspeed': (55, 70)
                },
                severity="CRITICAL"
            )
        }

    def _get_constant(self, key: str, default: Any) -> Any:
        """Safe constant access with fallback"""
        try:
            # Replace with actual constant access if available
            return ENGINE_FAILURE_DEFAULTS.get(key, default)
        except (AttributeError, KeyError):
            return default
    
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
