"""Procedure S (PS): updates human state from new pose statement."""

from __future__ import annotations

from dataclasses import dataclass

from ontologies.human_state_ontology import HumanState
from ontologies.perception_ontology import PoseStatement


@dataclass
class ProcedureS:
    human_state: HumanState

    def update_from_pose_statement(self, pose_stmt: PoseStatement) -> None:
        self.human_state.update(pose_stmt.label, pose_stmt.end_time)

