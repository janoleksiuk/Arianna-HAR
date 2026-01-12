"""
Procedure A (PA): action recognition + early intent inference (multi-human).

- detect_action(human_id): final action recognition (suffix match + optional constraints)
- compute_early_intent(human_id): returns candidate actions + families and best family

Works even when:
- No time constraints are defined (constraints are optional)
- No families are built (families optional)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ontologies.human_action_ontology import (
    ActionDefinition,
    ActionInstance,
    ActionFamily,
    StepConstraint,
    ActionConstraint,
)
from ontologies.memory_storage import MultiHumanMemoryStore


def _all_prefixes(seq: List[str]) -> List[List[str]]:
    return [seq[:i] for i in range(1, len(seq) + 1)]


@dataclass(frozen=True)
class EarlyIntent:
    candidate_actions: Dict[str, int]          # action -> best matched prefix length
    candidate_families: Dict[str, int]         # family_id -> prefix length (full prefix matched)
    best_family_id: Optional[str]
    best_family_prefix_len: int


@dataclass
class ProcedureA:
    action_defs: Dict[str, ActionDefinition]
    memory_store: MultiHumanMemoryStore
    families: Optional[Dict[str, ActionFamily]] = None

    # -------------------------
    # Constraint checking helpers
    # -------------------------
    def _check_step_constraints(
        self,
        pose_segments,
        seq_len: int,
        step_constraints: Optional[List[StepConstraint]],
    ) -> bool:
        if step_constraints is None:
            return True

        matched_segments = pose_segments[-seq_len:]
        if len(step_constraints) != len(matched_segments):
            return False

        for i, (seg, c) in enumerate(zip(matched_segments, step_constraints)):
            if seg.label != c.pose:
                return False

            dur = seg.duration
            if c.min_duration is not None and dur < c.min_duration:
                return False
            if c.max_duration is not None and dur > c.max_duration:
                return False

            if i > 0 and c.max_gap_after_prev is not None:
                prev = matched_segments[i - 1]
                gap = seg.start_time - prev.end_time
                if gap > c.max_gap_after_prev:
                    return False

        return True

    def _check_action_constraint(
        self,
        pose_segments,
        seq_len: int,
        action_constraint: Optional[ActionConstraint],
    ) -> Tuple[bool, float]:
        matched_segments = pose_segments[-seq_len:]
        start_t = matched_segments[0].start_time
        end_t = matched_segments[-1].end_time
        total_dur = end_t - start_t

        if action_constraint is None:
            return True, start_t

        if action_constraint.min_total_duration is not None and total_dur < action_constraint.min_total_duration:
            return False, start_t
        if action_constraint.max_total_duration is not None and total_dur > action_constraint.max_total_duration:
            return False, start_t

        return True, start_t

    # -------------------------
    # Final action recognition (per human)
    # -------------------------
    def detect_action(self, human_id: str, now_t: float) -> Optional[ActionInstance]:
        memory = self.memory_store.get(human_id)
        labels = memory.pose_label_sequence()
        pose_segments = memory.pose_segments

        for action_name, adef in self.action_defs.items():
            for seq_idx, seq in enumerate(adef.sequences):
                n = len(seq)
                if n <= len(labels) and labels[-n:] == seq:
                    step_constraints = None
                    if adef.step_constraints is not None and seq_idx < len(adef.step_constraints):
                        step_constraints = adef.step_constraints[seq_idx]

                    if not self._check_step_constraints(pose_segments, n, step_constraints):
                        continue

                    ok_action, start_t = self._check_action_constraint(pose_segments, n, adef.action_constraint)
                    if not ok_action:
                        continue

                    inst = ActionInstance(
                        name=action_name,
                        matched_sequence=seq,
                        start_time=start_t,
                        end_time=now_t,
                        confidence=1.0,
                    )
                    memory.recognized_actions.append(inst)
                    return inst

        return None

    # -------------------------
    # Early intent (per human)
    # -------------------------
    def compute_early_intent(self, human_id: str) -> EarlyIntent:
        memory = self.memory_store.get(human_id)
        labels = memory.pose_label_sequence()

        # Candidate actions based on prefix matches
        candidate_actions: Dict[str, int] = {}
        for action_name, adef in self.action_defs.items():
            best = 0
            for seq in adef.sequences:
                for pref in _all_prefixes(seq):
                    m = len(pref)
                    if m <= len(labels) and labels[-m:] == pref:
                        best = max(best, m)
            if best > 0:
                candidate_actions[action_name] = best

        # Candidate families: full family prefix must match suffix
        candidate_families: Dict[str, int] = {}
        best_family_id: Optional[str] = None
        best_family_len: int = 0

        if self.families:
            for fam_id, fam in self.families.items():
                pref = fam.prefix
                m = len(pref)
                if m <= len(labels) and labels[-m:] == pref:
                    candidate_families[fam_id] = m
                    if m > best_family_len:
                        best_family_len = m
                        best_family_id = fam_id

        return EarlyIntent(
            candidate_actions=candidate_actions,
            candidate_families=candidate_families,
            best_family_id=best_family_id,
            best_family_prefix_len=best_family_len,
        )
