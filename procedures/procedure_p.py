"""Procedure P (PP): perception → pose statements (multi-human).

Receives raw pose labels and updates the pose segment buffer by compressing
consecutive duplicates into intervals, per human_id.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from ontologies.perception_ontology import PoseStatement
from ontologies.memory_storage import MultiHumanMemoryStore
from config import MAX_POSE_BUFFER_LEN


@dataclass
class ProcedureP:
    memory_store: MultiHumanMemoryStore

    def ingest_pose_label(self, pose_label: str, human_id: str, t: float | None = None) -> PoseStatement:
        if t is None:
            t = time.time()

        memory = self.memory_store.get(human_id)

        # compress consecutive duplicates (per human)
        last = memory.pose_segments[-1] if memory.pose_segments else None
        if last and last.label == pose_label:
            last.extend_to(t)
            return last

        stmt = PoseStatement(label=pose_label, start_time=t, end_time=t)
        memory.pose_segments.append(stmt)

        # enforce max buffer length (per human)
        if len(memory.pose_segments) > MAX_POSE_BUFFER_LEN:
            memory.pose_segments = memory.pose_segments[-MAX_POSE_BUFFER_LEN:]

        return stmt
