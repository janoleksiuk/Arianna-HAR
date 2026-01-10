from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class StepConstraint:
    """Optional constraints for a single pose step within an action sequence."""
    pose: str
    min_duration: Optional[float] = None        # seconds
    max_duration: Optional[float] = None        # seconds
    max_gap_after_prev: Optional[float] = None  # seconds


@dataclass(frozen=True)
class ActionConstraint:
    """Optional constraints over the whole action."""
    min_total_duration: Optional[float] = None  # seconds
    max_total_duration: Optional[float] = None  # seconds


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    sequences: List[List[str]]

    # Optional: constraints per sequence (parallel list to `sequences`)
    # Each element is either None (no constraints) or list of StepConstraint with same length as that sequence.
    step_constraints: Optional[List[Optional[List[StepConstraint]]]] = None

    # Optional: constraints for the whole action (None = no constraint)
    action_constraint: Optional[ActionConstraint] = None


@dataclass
class ActionInstance:
    name: str
    matched_sequence: List[str]
    end_time: float
    start_time: Optional[float] = None
    confidence: float = 1.0


def build_action_definitions(
    action_def_dict: Dict[str, List[List[str]]],
) -> Dict[str, ActionDefinition]:
    """Build action definitions without constraints (backward-compatible)."""
    return {
        k: ActionDefinition(name=k, sequences=v)
        for k, v in action_def_dict.items()
    }
