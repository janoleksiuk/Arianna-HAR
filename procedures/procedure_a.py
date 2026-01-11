from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ontologies.human_action_ontology import ActionDefinition, ActionInstance, StepConstraint, ActionConstraint
from ontologies.memory_storage import EpisodeMemory
from utils.visualizer import format_candidates


def _all_prefixes(seq: List[str]) -> List[List[str]]:
    return [seq[:i] for i in range(1, len(seq) + 1)]


@dataclass
class ProcedureA:
    action_defs: Dict[str, ActionDefinition]
    memory: EpisodeMemory

    def _check_step_constraints(
        self,
        pose_segments,
        seq_len: int,
        step_constraints: Optional[List[StepConstraint]],
    ) -> bool:
        """Validate optional per-step constraints against the matched suffix pose segments."""
        if step_constraints is None:
            return True  # no constraints

        # Extract the last seq_len pose segments (the matched suffix)
        matched_segments = pose_segments[-seq_len:]

        if len(step_constraints) != len(matched_segments):
            return False  # invalid configuration

        for i, (seg, c) in enumerate(zip(matched_segments, step_constraints)):
            # Pose must match config pose (safety)
            if seg.label != c.pose:
                return False

            dur = seg.duration
            if c.min_duration is not None and dur < c.min_duration:
                return False
            if c.max_duration is not None and dur > c.max_duration:
                return False

            # Gap constraint relative to previous segment
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
    ) -> Tuple[bool, Optional[float]]:
        """Validate optional whole-action constraints; return (ok, start_time)."""
        matched_segments = pose_segments[-seq_len:]
        start_t = matched_segments[0].start_time
        end_t = matched_segments[-1].end_time
        total = end_t - start_t

        if action_constraint is None:
            return True, start_t

        if action_constraint.min_total_duration is not None and total < action_constraint.min_total_duration:
            return False, start_t
        if action_constraint.max_total_duration is not None and total > action_constraint.max_total_duration:
            return False, start_t

        return True, start_t

    def detect_action(self, now_t: float) -> Optional[ActionInstance]:
        """Return an ActionInstance if any action matches the current suffix and constraints pass."""
        labels = self.memory.pose_label_sequence()
        pose_segments = self.memory.pose_segments

        for action_name, adef in self.action_defs.items():
            for idx, seq in enumerate(adef.sequences):
                n = len(seq)
                if n <= len(labels) and labels[-n:] == seq:
                    # Check constraints if present
                    step_constraints = None
                    if adef.step_constraints is not None and idx < len(adef.step_constraints):
                        step_constraints = adef.step_constraints[idx]

                    ok_steps = self._check_step_constraints(pose_segments, n, step_constraints)
                    if not ok_steps:
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
                    self.memory.recognized_actions.append(inst)
                    return inst

        return None

    def compute_candidate_actions(self) -> Dict[str, List[int]]:
        """Candidate actions whose prefix matches some suffix (constraints not checked for candidates)."""
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
