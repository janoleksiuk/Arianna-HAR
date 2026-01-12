"""Memory Storage (multi-human ready).

- EpisodeMemory stores per-human pose segments, recognized actions, executed tasks.
- MultiHumanMemoryStore holds a mapping: human_id -> EpisodeMemory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .perception_ontology import PoseStatement
from .human_action_ontology import ActionInstance


@dataclass
class EpisodeMemory:
    pose_segments: List[PoseStatement] = field(default_factory=list)
    recognized_actions: List[ActionInstance] = field(default_factory=list)
    executed_tasks: List[str] = field(default_factory=list)

    def clear(self) -> None:
        self.pose_segments.clear()
        self.recognized_actions.clear()
        self.executed_tasks.clear()

    def last_pose_label(self) -> Optional[str]:
        return self.pose_segments[-1].label if self.pose_segments else None

    def pose_label_sequence(self) -> List[str]:
        return [p.label for p in self.pose_segments]


@dataclass
class MultiHumanMemoryStore:
    """Maps each human_id to its own EpisodeMemory (pose buffer + action/task history)."""
    by_human: Dict[str, EpisodeMemory] = field(default_factory=dict)

    def get(self, human_id: str) -> EpisodeMemory:
        if human_id not in self.by_human:
            self.by_human[human_id] = EpisodeMemory()
        return self.by_human[human_id]

    def clear_human(self, human_id: str) -> None:
        self.get(human_id).clear()
