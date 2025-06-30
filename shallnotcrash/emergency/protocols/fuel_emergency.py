#!/usr/bin/env python3
"""
Cessna 172P Fuel Emergency Protocol
Complete constant-driven implementation with no hardcoded values
"""
import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any

# Corrected imports based on project structure
from ...airplane.constants import C172PConstants
from ..constants import FuelThresholds, EmergencyProcedures, EmergencyConfig, EmergencySeverity

@dataclass
class FuelEmergencyStage:
    name: str
    actions: List[str]
    conditions: Dict[str, Tuple[float, float]]  # (param_name, (min, max))
    severity: EmergencySeverity

class FuelEmergencyProtocol:
    """Dynamic fuel emergency management system"""
    
    def __init__(self):
        self.stages = self._build_stages()
        self._last_tank_switch = 0
        self._current_stage_index = 0

    def _build_stages(self) -> List[FuelEmergencyStage]:
        """Construct all procedure stages from constants"""
        return [
            FuelEmergencyStage(
                name="Imbalance Warning",
                actions=[
                    f"Maximum imbalance: {FuelThresholds.IMBALANCE['CRITICAL']} gal",
                    "Current imbalance: {imbalance:.1f} gal",
                    f"Switch tanks every {EmergencyProcedures.FUEL_EMERGENCY['TANK_SWITCH_INTERVAL']} min",
                    "Monitor fuel flow"
                ],
                conditions={
                    'imbalance': (FuelThresholds.IMBALANCE['WARNING'], 
                                FuelThresholds.IMBALANCE['CRITICAL'])
                },
                severity=EmergencySeverity.WARNING
            ),
            FuelEmergencyStage(
                name="Critical Fuel State",
                actions=[
                    "Total remaining: {total_fuel:.1f} gal",
                    "Estimated endurance: {endurance:.0f} min",
                    f"Fuel selector: BOTH",
                    f"Mixture: RICH",
                    f"Power: Reduce to {C172PConstants.ENGINE['REDLINE_RPM']*0.65:.0f} RPM",
                    f"Declare emergency if < {FuelThresholds.QTY['CRITICAL']} gal"
                ],
                conditions={
                    'total_fuel': (0, FuelThresholds.QTY['CRITICAL'])
                },
                severity=EmergencySeverity.EMERGENCY
            ),
            FuelEmergencyStage(
                name="Fuel Starvation",
                actions=[
                    "Immediate actions:",
                    f"1. Fuel selector: SWITCH TANK",
                    f"2. Fuel pump: ON for {EmergencyProcedures.FUEL_EMERGENCY['PUMP_DURATION']} sec",
                    f"3. Mixture: RICH for {EmergencyProcedures.FUEL_EMERGENCY['MIXTURE_HOLD']} sec",
                    f"4. Throttle: CYCLE every {EmergencyProcedures.FUEL_EMERGENCY['THROTTLE_CYCLE_INTERVAL']} sec",
                    f"Attempt restart if RPM < {C172PConstants.ENGINE['IDLE_RPM']}"
                ],
                conditions={
                    'fuel_flow': (0, FuelThresholds.STARVATION['FLOW_WARNING'])
                },
                severity=EmergencySeverity.CRITICAL
            )
        ]

    def get_actions(self, telemetry: Dict[str, float]) -> List[str]:
        """Get formatted checklist with real-time values"""
        current_stage = self._determine_stage(telemetry)
        if not current_stage:
            return []

        # Update tank switch timer if relevant
        if "Fuel selector: SWITCH TANK" in current_stage.actions:
            self._last_tank_switch = time.time()

        # Format actions with live values
        formatted_actions = []
        for action in current_stage.actions:
            try:
                formatted_actions.append(action.format(**telemetry))
            except KeyError:
                formatted_actions.append(action)

        return [
            f"=== FUEL {current_stage.name.upper()} ===",
            f"Severity: {current_stage.severity.name}",
            *formatted_actions,
            f"Next update in {EmergencyConfig.TELEMETRY_RATE} sec"
        ]

    def _determine_stage(self, telemetry: Dict) -> Optional[FuelEmergencyStage]:
        """Determine current emergency stage"""
        enriched = self._enrich_telemetry(telemetry)
        for i, stage in enumerate(self.stages):
            if self._check_conditions(stage, enriched):
                self._current_stage_index = i
                return stage
        return None

    def _enrich_telemetry(self, telemetry: Dict) -> Dict:
        """Add calculated fuel parameters"""
        telemetry['imbalance'] = abs(telemetry.get('fuel_left', 0) - 
                                   telemetry.get('fuel_right', 0))
        telemetry['total_fuel'] = (telemetry.get('fuel_left', 0) + 
                                  telemetry.get('fuel_right', 0))
        telemetry['endurance'] = self._calculate_endurance(
            telemetry['total_fuel'],
            telemetry.get('fuel_flow', C172PConstants.ENGINE['MIN_FUEL_FLOW_IDLE'])
        )
        return telemetry

    def _calculate_endurance(self, total_fuel: float, fuel_flow: float) -> float:
        """Calculate remaining flight time in minutes"""
        if fuel_flow <= 0:
            return 0
        return (total_fuel / fuel_flow) * 60

    def _check_conditions(self, stage: FuelEmergencyStage, 
                        telemetry: Dict) -> bool:
        """Verify if stage conditions are met"""
        for param, value_range in stage.conditions.items():
            value = telemetry.get(param)
            if value is None:
                return False
            min_val, max_val = value_range
            if not (min_val <= value <= max_val):
                return False
        return True

    def reset(self):
        """Reset protocol state between flights"""
        self._last_tank_switch = 0
        self._current_stage_index = 0

# Protocol instance (singleton pattern)
FUEL_EMERGENCY_PROTOCOL = FuelEmergencyProtocol()

def get_fuel_emergency_checklist(telemetry: Dict) -> List[str]:
    """Get formatted checklist for current fuel state"""
    return FUEL_EMERGENCY_PROTOCOL.get_actions(telemetry)

def reset_protocol():
    """Reset protocol state between flights"""
    FUEL_EMERGENCY_PROTOCOL.reset()
