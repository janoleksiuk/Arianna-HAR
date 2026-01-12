"""Procedure S (PS): update human state (multi-human).

Maintains a dict of HumanState objects keyed by human_id.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ontologies.human_state_ontology import HumanState
from ontologies.perception_ontology import PoseStatement


@dataclass
class ProcedureS:
    human_states: Dict[str, HumanState]

    def get_state(self, human_id: str) -> HumanState:
        if human_id not in self.human_states:
            self.human_states[human_id] = HumanState(human_id=human_id)
        return self.human_states[human_id]

    def update_from_pose_statement(self, pose_stmt: PoseStatement, human_id: str) -> None:
        state = self.get_state(human_id)
        state.update(pose_stmt.label, pose_stmt.end_time)
