"""Human State Ontology (OS) - holds the current human pose."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class HumanState:
    human_id: str = "human_1"
    current_pose: Optional[str] = None
    last_update_time: Optional[float] = None

    def update(self, pose_label: str, t: float) -> None:
        self.current_pose = pose_label
        self.last_update_time = t

