"""Memory Storage - stores recent pose segments and recognized actions/tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

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

