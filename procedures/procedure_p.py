"""Procedure P (PP): perception → pose statements (compress duplicates)."""

from __future__ import annotations

import time
from dataclasses import dataclass

from ontologies.perception_ontology import PoseStatement
from ontologies.memory_storage import EpisodeMemory
from config import MAX_POSE_BUFFER_LEN


@dataclass
class ProcedureP:
    memory: EpisodeMemory

    def ingest_pose_label(self, pose_label: str, t: float | None = None) -> PoseStatement:
        if t is None:
            t = time.time()

        last = self.memory.pose_segments[-1] if self.memory.pose_segments else None
        if last and last.label == pose_label:
            last.extend_to(t)
            return last

        stmt = PoseStatement(label=pose_label, start_time=t, end_time=t)
        self.memory.pose_segments.append(stmt)

        if len(self.memory.pose_segments) > MAX_POSE_BUFFER_LEN:
            self.memory.pose_segments = self.memory.pose_segments[-MAX_POSE_BUFFER_LEN:]

        return stmt

