"""Upper Ontology (OU) - coordination concepts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional


class SystemMode(str, Enum):
    RECOGNIZING = "recognizing"
    EXECUTING_TASK = "executing_task"


@dataclass
class OntologyMeta:
    name: str
    description: str = ""
    version: str = "0.1"


@dataclass
class Condition:
    """A boolean check used by events."""
    name: str
    check: Callable[[], bool]
    last_value: bool = False


@dataclass
class Event:
    """An event becomes true when all its conditions become true."""
    name: str
    conditions: Dict[str, Condition] = field(default_factory=dict)

    def evaluate(self) -> bool:
        if not self.conditions:
            return False
        return all(c.check() for c in self.conditions.values())


@dataclass
class Procedure:
    """A procedure can be scheduled when an event triggers."""
    name: str
    run: Callable[[], None]
    requires_event: Optional[Event] = None


@dataclass
class UpperOntologyState:
    """Global runtime state."""
    mode: SystemMode = SystemMode.RECOGNIZING

    def set_mode(self, mode: SystemMode) -> None:
        self.mode = mode

