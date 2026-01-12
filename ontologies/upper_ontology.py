"""
Upper Ontology (OU) - coordination concepts.

In Arianna+-style architectures, OU defines global coordination:
- system mode
- events/conditions triggering procedures

In this Python prototype:
- SystemMode + UpperOntologyState remain the global coordination state.
- RuntimeEvent is a lightweight event object (for the scheduler).
- Condition is a callable predicate evaluated by the scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional


class SystemMode(str, Enum):
    RECOGNIZING = "recognizing"
    EXECUTING_TASK = "executing_task"


@dataclass
class OntologyMeta:
    name: str
    description: str = ""
    version: str = "0.1"


@dataclass(frozen=True)
class RuntimeEvent:
    """A runtime event emitted inside the scheduler."""
    name: str
    payload: Dict[str, Any]
    t: float


@dataclass
class Condition:
    """
    A boolean predicate over (scheduler, event).

    - If True, the procedure can run.
    - If False, the procedure is skipped.
    """
    name: str
    check: Callable[[Any, RuntimeEvent], bool]


@dataclass
class Procedure:
    """
    A procedure runnable by the scheduler.

    The scheduler decides *when* to run it based on:
    - which event name triggered it
    - its conditions
    """
    name: str
    run: Callable[[Any, RuntimeEvent], None]
    conditions: Dict[str, Condition] = field(default_factory=dict)

    def can_run(self, scheduler: Any, event: RuntimeEvent) -> bool:
        return all(c.check(scheduler, event) for c in self.conditions.values())


@dataclass
class UpperOntologyState:
    """Global runtime state."""
    mode: SystemMode = SystemMode.RECOGNIZING

    def set_mode(self, mode: SystemMode) -> None:
        self.mode = mode
