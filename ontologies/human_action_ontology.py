"""Human Action Ontology (OA) - action templates and recognized instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    sequences: List[List[str]]


@dataclass
class ActionInstance:
    """A recognized action occurrence."""
    name: str
    matched_sequence: List[str]
    end_time: float
    start_time: Optional[float] = None


def build_action_definitions(action_def_dict: Dict[str, List[List[str]]]) -> Dict[str, ActionDefinition]:
    return {k: ActionDefinition(name=k, sequences=v) for k, v in action_def_dict.items()}

