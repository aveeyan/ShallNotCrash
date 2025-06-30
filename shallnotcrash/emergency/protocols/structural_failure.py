#!/usr/bin/env python3
"""
Structural Failure Emergency Protocol for Cessna 172P
Handles wing damage, control surface failures, and structural integrity emergencies
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

# Relative imports within shallnotcrash package
from ...constants.flightgear import FGProps
from ..constants import EmergencySeverity, EmergencyProcedures, AerodynamicThresholds

class StructuralFailureStage(Enum):
    PRIMARY_CONTROL_LOSS = auto()
    SECONDARY_DAMAGE_CONTAINMENT = auto()
    EMERGENCY_LANDING_PREPARATION = auto()

@dataclass
class ProtocolStage:
    name: str
    actions: List[str]
    conditions: Dict[str, Tuple[float, float]]
    severity: EmergencySeverity

class StructuralFailureProtocol:
    """Stateful structural failure emergency protocol"""
    def __init__(self):
        self.stages = self._build_stages()
        self._current_stage = StructuralFailureStage.PRIMARY_CONTROL_LOSS
        self._damage_contained = False
    
    def _build_stages(self) -> Dict[StructuralFailureStage, ProtocolStage]:
        """Construct structural failure response protocol"""
        return {
            StructuralFailureStage.PRIMARY_CONTROL_LOSS: ProtocolStage(
                name="Primary Control Loss",
                actions=[
                    "Maintain aircraft control at all costs",
                    "Reduce airspeed to maneuvering speed (V_A)",
                    "Neutralize control inputs",
                    "Assess control effectiveness: Ailerons/Elevator/Rudder",
                    "Trim for hands-off flight if possible"
                ],
                conditions={
                    'vibration_level': (AerodynamicThresholds.VIBRATION['CRITICAL'], 10.0),
                    'control_effectiveness': (0, 0.5)
                },
                severity=EmergencySeverity.EMERGENCY
            ),
            StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT: ProtocolStage(
                name="Secondary Damage Containment",
                actions=[
                    "Secure loose items in cockpit",
                    "Close all vents and air outlets",
                    "Disable non-essential electrical systems",
                    "Verify structural integrity indicators",
                    "Prepare for potential cabin depressurization"
                ],
                conditions={
                    'airspeed': (0, AerodynamicThresholds.OVERSPEED['WARNING']),
                    'structural_integrity': (0.3, 0.7)
                },
                severity=EmergencySeverity.CRITICAL
            ),
            StructuralFailureStage.EMERGENCY_LANDING_PREPARATION: ProtocolStage(
                name="Emergency Landing Preparation",
                actions=[
                    "Declare MAYDAY with position and intentions",
                    "Secure cabin for impact: Seatbelts tightened, loose objects secured",
                    "Configure for landing: Flaps as structural integrity allows",
                    "Identify landing site: Prefer open fields over populated areas",
                    "Brief passengers on brace position and evacuation plan"
                ],
                conditions={
                    'altitude_agl': (0, EmergencyProcedures.STRUCTURAL_FAILURE['MIN_LANDING_ALT']),
                    'distance_to_landing': (0, 5)  # NM
                },
                severity=EmergencySeverity.EMERGENCY
            )
        }
    
    def get_actions(self, telemetry: Dict[str, float]) -> List[str]:
        """Get current emergency checklist based on flight state"""
        self._update_stage(telemetry)
        return self.stages[self._current_stage].actions
    
    def _update_stage(self, telemetry: Dict[str, float]):
        """Transition between protocol stages based on conditions"""
        # Enrich telemetry with derived parameters
        enriched_telemetry = self._enrich_telemetry(telemetry)
        
        # Check stage progression conditions
        if self._current_stage == StructuralFailureStage.PRIMARY_CONTROL_LOSS:
            if self._check_conditions(
                self.stages[StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT].conditions,
                enriched_telemetry
            ):
                self._current_stage = StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT
                
        elif self._current_stage == StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT:
            if self._check_conditions(
                self.stages[StructuralFailureStage.EMERGENCY_LANDING_PREPARATION].conditions,
                enriched_telemetry
            ):
                self._current_stage = StructuralFailureStage.EMERGENCY_LANDING_PREPARATION
                
    def _enrich_telemetry(self, telemetry: Dict[str, float]) -> Dict[str, float]:
        """Calculate structural integrity metrics"""
        # Calculate control effectiveness ratio
        telemetry['control_effectiveness'] = self._calculate_control_effectiveness(
            telemetry.get(FGProps.CONTROLS.AILERON, 0),
            telemetry.get(FGProps.CONTROLS.ELEVATOR, 0),
            telemetry.get(FGProps.CONTROLS.RUDDER, 0)
        )
        
        # Estimate structural integrity index
        telemetry['structural_integrity'] = self._estimate_structural_integrity(
            telemetry.get('vibration_level', 0),
            telemetry.get('g_load', 1.0)
        )
        
        return telemetry
    
    def _calculate_control_effectiveness(self, aileron: float, elevator: float, rudder: float) -> float:
        """Calculate normalized control effectiveness (0-1 scale)"""
        # Simple heuristic: control effectiveness reduces with asymmetric inputs
        asymmetry_score = abs(aileron) + abs(elevator) + abs(rudder)
        return max(0, min(1, 1.0 - (asymmetry_score / 3.0)))
    
    def _estimate_structural_integrity(self, vibration: float, g_load: float) -> float:
        """Estimate structural integrity (0-1 scale) based on stress factors"""
        # Simple heuristic: integrity decreases with high vibration and g-loads
        vibration_factor = min(1, vibration / 5.0)  # 5g vibration is max
        g_load_factor = min(1, abs(g_load - 1.0) / 2.0)  # 3g is max
        return max(0, 1.0 - (vibration_factor + g_load_factor)/2.0)
    
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
    
    def reset(self):
        """Reset protocol state between flights"""
        self._current_stage = StructuralFailureStage.PRIMARY_CONTROL_LOSS
        self._damage_contained = False

    def get_stage_name(self, telemetry: Dict[str, float]) -> str:
        """Get human-readable stage name"""
        self._update_stage(telemetry)
        return self.stages[self._current_stage].name

# Singleton instance for system-wide use
STRUCTURAL_FAILURE_PROTOCOL = StructuralFailureProtocol()

def get_current_stage(telemetry: Dict[str, float]) -> str:
    """Get current stage name for monitoring systems"""
    return STRUCTURAL_FAILURE_PROTOCOL.get_stage_name(telemetry)

def reset_protocol():
    """Reset protocol state (for simulation/testing)"""
    STRUCTURAL_FAILURE_PROTOCOL.reset()#!/usr/bin/env python3
"""
Structural Failure Emergency Protocol for Cessna 172P
Handles wing damage, control surface failures, and structural integrity emergencies
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

# Relative imports within shallnotcrash package
from ...constants.flightgear import FGProps
from ..constants import EmergencySeverity, EmergencyProcedures, AerodynamicThresholds

class StructuralFailureStage(Enum):
    PRIMARY_CONTROL_LOSS = auto()
    SECONDARY_DAMAGE_CONTAINMENT = auto()
    EMERGENCY_LANDING_PREPARATION = auto()

@dataclass
class ProtocolStage:
    name: str
    actions: List[str]
    conditions: Dict[str, Tuple[float, float]]
    severity: EmergencySeverity

class StructuralFailureProtocol:
    """Stateful structural failure emergency protocol"""
    def __init__(self):
        self.stages = self._build_stages()
        self._current_stage = StructuralFailureStage.PRIMARY_CONTROL_LOSS
        self._damage_contained = False
    
    def _build_stages(self) -> Dict[StructuralFailureStage, ProtocolStage]:
        """Construct structural failure response protocol"""
        return {
            StructuralFailureStage.PRIMARY_CONTROL_LOSS: ProtocolStage(
                name="Primary Control Loss",
                actions=[
                    "Maintain aircraft control at all costs",
                    "Reduce airspeed to maneuvering speed (V_A)",
                    "Neutralize control inputs",
                    "Assess control effectiveness: Ailerons/Elevator/Rudder",
                    "Trim for hands-off flight if possible"
                ],
                conditions={
                    'vibration_level': (AerodynamicThresholds.VIBRATION['CRITICAL'], 10.0),
                    'control_effectiveness': (0, 0.5)
                },
                severity=EmergencySeverity.EMERGENCY
            ),
            StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT: ProtocolStage(
                name="Secondary Damage Containment",
                actions=[
                    "Secure loose items in cockpit",
                    "Close all vents and air outlets",
                    "Disable non-essential electrical systems",
                    "Verify structural integrity indicators",
                    "Prepare for potential cabin depressurization"
                ],
                conditions={
                    'airspeed': (0, AerodynamicThresholds.OVERSPEED['WARNING']),
                    'structural_integrity': (0.3, 0.7)
                },
                severity=EmergencySeverity.CRITICAL
            ),
            StructuralFailureStage.EMERGENCY_LANDING_PREPARATION: ProtocolStage(
                name="Emergency Landing Preparation",
                actions=[
                    "Declare MAYDAY with position and intentions",
                    "Secure cabin for impact: Seatbelts tightened, loose objects secured",
                    "Configure for landing: Flaps as structural integrity allows",
                    "Identify landing site: Prefer open fields over populated areas",
                    "Brief passengers on brace position and evacuation plan"
                ],
                conditions={
                    'altitude_agl': (0, EmergencyProcedures.STRUCTURAL_FAILURE['MIN_LANDING_ALT']),
                    'distance_to_landing': (0, 5)  # NM
                },
                severity=EmergencySeverity.EMERGENCY
            )
        }
    
    def get_actions(self, telemetry: Dict[str, float]) -> List[str]:
        """Get current emergency checklist based on flight state"""
        self._update_stage(telemetry)
        return self.stages[self._current_stage].actions
    
    def _update_stage(self, telemetry: Dict[str, float]):
        """Transition between protocol stages based on conditions"""
        # Enrich telemetry with derived parameters
        enriched_telemetry = self._enrich_telemetry(telemetry)
        
        # Check stage progression conditions
        if self._current_stage == StructuralFailureStage.PRIMARY_CONTROL_LOSS:
            if self._check_conditions(
                self.stages[StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT].conditions,
                enriched_telemetry
            ):
                self._current_stage = StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT
                
        elif self._current_stage == StructuralFailureStage.SECONDARY_DAMAGE_CONTAINMENT:
            if self._check_conditions(
                self.stages[StructuralFailureStage.EMERGENCY_LANDING_PREPARATION].conditions,
                enriched_telemetry
            ):
                self._current_stage = StructuralFailureStage.EMERGENCY_LANDING_PREPARATION
                
    def _enrich_telemetry(self, telemetry: Dict[str, float]) -> Dict[str, float]:
        """Calculate structural integrity metrics"""
        # Calculate control effectiveness ratio
        telemetry['control_effectiveness'] = self._calculate_control_effectiveness(
            telemetry.get(FGProps.CONTROLS.AILERON, 0),
            telemetry.get(FGProps.CONTROLS.ELEVATOR, 0),
            telemetry.get(FGProps.CONTROLS.RUDDER, 0)
        )
        
        # Estimate structural integrity index
        telemetry['structural_integrity'] = self._estimate_structural_integrity(
            telemetry.get('vibration_level', 0),
            telemetry.get('g_load', 1.0)
        )
        
        return telemetry
    
    def _calculate_control_effectiveness(self, aileron: float, elevator: float, rudder: float) -> float:
        """Calculate normalized control effectiveness (0-1 scale)"""
        # Simple heuristic: control effectiveness reduces with asymmetric inputs
        asymmetry_score = abs(aileron) + abs(elevator) + abs(rudder)
        return max(0, min(1, 1.0 - (asymmetry_score / 3.0)))
    
    def _estimate_structural_integrity(self, vibration: float, g_load: float) -> float:
        """Estimate structural integrity (0-1 scale) based on stress factors"""
        # Simple heuristic: integrity decreases with high vibration and g-loads
        vibration_factor = min(1, vibration / 5.0)  # 5g vibration is max
        g_load_factor = min(1, abs(g_load - 1.0) / 2.0)  # 3g is max
        return max(0, 1.0 - (vibration_factor + g_load_factor)/2.0)
    
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
    
    def reset(self):
        """Reset protocol state between flights"""
        self._current_stage = StructuralFailureStage.PRIMARY_CONTROL_LOSS
        self._damage_contained = False

    def get_stage_name(self, telemetry: Dict[str, float]) -> str:
        """Get human-readable stage name"""
        self._update_stage(telemetry)
        return self.stages[self._current_stage].name

# Singleton instance for system-wide use
STRUCTURAL_FAILURE_PROTOCOL = StructuralFailureProtocol()

def get_current_stage(telemetry: Dict[str, float]) -> str:
    """Get current stage name for monitoring systems"""
    return STRUCTURAL_FAILURE_PROTOCOL.get_stage_name(telemetry)

def reset_protocol():
    """Reset protocol state (for simulation/testing)"""
    STRUCTURAL_FAILURE_PROTOCOL.reset()