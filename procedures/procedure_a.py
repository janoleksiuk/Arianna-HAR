"""Procedure A (PA): action recognition via suffix matching, plus early candidates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from ontologies.human_action_ontology import ActionDefinition, ActionInstance
from ontologies.memory_storage import EpisodeMemory
from utils.visualizer import format_candidates


def _all_prefixes(seq: List[str]) -> List[List[str]]:
    return [seq[:i] for i in range(1, len(seq) + 1)]


@dataclass
class ProcedureA:
    action_defs: Dict[str, ActionDefinition]
    memory: EpisodeMemory

    def detect_action(self, now_t: float) -> Optional[ActionInstance]:
        """Return an ActionInstance if any action matches the current suffix."""
        labels = self.memory.pose_label_sequence()
        for action_name, adef in self.action_defs.items():
            for seq in adef.sequences:
                n = len(seq)
                if n <= len(labels) and labels[-n:] == seq:
                    inst = ActionInstance(name=action_name, matched_sequence=seq, end_time=now_t)
                    self.memory.recognized_actions.append(inst)
                    return inst
        return None

    def compute_candidate_actions(self) -> Dict[str, List[int]]:
        """Compute candidate actions whose prefix matches some suffix of current labels."""
        labels = self.memory.pose_label_sequence()
        candidates: Dict[str, List[int]] = {}

        for action_name, adef in self.action_defs.items():
            for seq in adef.sequences:
                for pref in _all_prefixes(seq):
                    m = len(pref)
                    if m <= len(labels) and labels[-m:] == pref:
                        candidates.setdefault(action_name, []).append(m)
        return candidates

    def debug_print_candidates(self, logger) -> None:
        candidates = self.compute_candidate_actions()
        logger.info(f"Candidates (early intent): {format_candidates(candidates)}")

