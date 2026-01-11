"""
Procedure A (PA): action recognition.

- Recognizes human actions as suffix matches over the compressed pose sequence.
- Optionally enforces time constraints if defined in the action ontology:
  * per-step constraints (min/max duration, max gap after previous)
  * whole-action constraints (min/max total duration)

It remains fully backward-compatible:
- If no constraints are defined, it behaves like the old exact suffix matcher.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ontologies.human_action_ontology import (
    ActionDefinition,
    ActionInstance,
    StepConstraint,
    ActionConstraint,
)
from ontologies.memory_storage import EpisodeMemory
from utils.visualizer import format_candidates


def _all_prefixes(seq: List[str]) -> List[List[str]]:
    return [seq[:i] for i in range(1, len(seq) + 1)]


@dataclass
class ProcedureA:
    action_defs: Dict[str, ActionDefinition]
    memory: EpisodeMemory

    # -------------------------
    # Constraint checking helpers
    # -------------------------
    def _check_step_constraints(
        self,
        pose_segments,
        seq_len: int,
        step_constraints: Optional[List[StepConstraint]],
    ) -> bool:
        """
        Validate optional per-step constraints against the matched suffix pose segments.

        Backward-compatible behavior:
          - step_constraints is None -> accept (no constraints)
        """
        if step_constraints is None:
            return True

        matched_segments = pose_segments[-seq_len:]

        # Safety: ensure configuration matches sequence length
        if len(step_constraints) != len(matched_segments):
            return False

        for i, (seg, c) in enumerate(zip(matched_segments, step_constraints)):
            # Sanity: ensure the constraint is tied to the same pose label
            if seg.label != c.pose:
                return False

            dur = seg.duration
            if c.min_duration is not None and dur < c.min_duration:
                return False
            if c.max_duration is not None and dur > c.max_duration:
                return False

            # Optional gap constraint relative to previous segment
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
        """
        Validate optional whole-action constraints.

        Returns:
          (ok, start_time_of_matched_action)

        Backward-compatible behavior:
          - action_constraint is None -> accept (no constraints)
        """
        matched_segments = pose_segments[-seq_len:]
        start_t = matched_segments[0].start_time
        end_t = matched_segments[-seq_len:].pop().end_time if False else matched_segments[-1].end_time
        total_dur = end_t - start_t

        if action_constraint is None:
            return True, start_t

        if action_constraint.min_total_duration is not None and total_dur < action_constraint.min_total_duration:
            return False, start_t
        if action_constraint.max_total_duration is not None and total_dur > action_constraint.max_total_duration:
            return False, start_t

        return True, start_t

    # -------------------------
    # Recognition
    # -------------------------
    def detect_action(self, now_t: float) -> Optional[ActionInstance]:
        """
        Return an ActionInstance if any action matches the current suffix
        AND (if constraints exist) constraints pass.
        """
        labels = self.memory.pose_label_sequence()
        pose_segments = self.memory.pose_segments

        for action_name, adef in self.action_defs.items():
            for seq_idx, seq in enumerate(adef.sequences):
                n = len(seq)

                # Strict suffix match on labels
                if n <= len(labels) and labels[-n:] == seq:
                    # Obtain per-sequence step constraints (if any)
                    step_constraints = None
                    if adef.step_constraints is not None:
                        if seq_idx < len(adef.step_constraints):
                            step_constraints = adef.step_constraints[seq_idx]

                    # Check per-step constraints
                    if not self._check_step_constraints(pose_segments, n, step_constraints):
                        continue

                    # Check whole-action constraints
                    ok_action, start_t = self._check_action_constraint(pose_segments, n, adef.action_constraint)
                    if not ok_action:
                        continue

                    # Success: create action instance
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

    # -------------------------
    # Early candidate reporting
    # -------------------------
    def compute_candidate_actions(self) -> Dict[str, List[int]]:
        """
        Compute candidate actions whose prefix matches some suffix of current labels.

        Note: constraints are NOT enforced for candidates (by design).
        Candidates are only for early intent / family narrowing.
        """
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
