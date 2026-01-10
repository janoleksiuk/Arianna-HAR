"""Robot Ontology (OR) - task definitions and behavior steps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class BehaviorStep:
    name: str
    params: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class TaskDefinition:
    name: str
    steps: List[BehaviorStep]


def build_task_definitions(task_def_dict: Dict[str, List[object]]) -> Dict[str, TaskDefinition]:
    out: Dict[str, TaskDefinition] = {}
    for task_name, step_defs in task_def_dict.items():
        steps = [BehaviorStep(s.name, s.params) for s in step_defs]
        out[task_name] = TaskDefinition(name=task_name, steps=steps)
    return out

