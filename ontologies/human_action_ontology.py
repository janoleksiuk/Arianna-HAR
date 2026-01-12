"""
Human Action Ontology (OA).

Defines action templates as sequences of pose labels.
Also defines ActionFamily objects built from shared prefixes (for early intent).

Constraints are supported but optional; current action set uses none by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class StepConstraint:
    """Optional constraints for a single pose step within an action sequence."""
    pose: str
    min_duration: Optional[float] = None        # seconds
    max_duration: Optional[float] = None        # seconds
    max_gap_after_prev: Optional[float] = None  # seconds


@dataclass(frozen=True)
class ActionConstraint:
    """Optional constraints over the whole action."""
    min_total_duration: Optional[float] = None  # seconds
    max_total_duration: Optional[float] = None  # seconds


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    sequences: List[List[str]]
    # Optional: constraints per sequence (parallel list to `sequences`)
    step_constraints: Optional[List[Optional[List[StepConstraint]]]] = None
    action_constraint: Optional[ActionConstraint] = None


@dataclass
class ActionInstance:
    """A recognized action occurrence."""
    name: str
    matched_sequence: List[str]
    end_time: float
    start_time: Optional[float] = None
    confidence: float = 1.0


@dataclass(frozen=True)
class ActionFamily:
    """A family groups actions that share a common prefix."""
    family_id: str
    prefix: List[str]
    members: Set[str]
    pre_task: Optional[str] = None


def build_action_definitions(
    action_def_dict: Dict[str, List[List[str]]],
    step_constraints_dict: Optional[Dict[str, List[List[dict]]]] = None,
) -> Dict[str, ActionDefinition]:
    """
    Build action definitions and attach optional step constraints.

    step_constraints_dict uses the same indexing as action_def_dict:
      - For each action, a list of sequences
      - For each sequence, a list of dict constraints per step
    """
    out: Dict[str, ActionDefinition] = {}

    for action_name, sequences in action_def_dict.items():
        step_constraints = None

        if step_constraints_dict and action_name in step_constraints_dict:
            raw = step_constraints_dict[action_name]

            converted: List[Optional[List[StepConstraint]]] = []
            for seq_idx, seq in enumerate(sequences):
                if seq_idx >= len(raw):
                    converted.append(None)
                    continue

                raw_seq_constraints = raw[seq_idx]
                if len(raw_seq_constraints) != len(seq):
                    raise ValueError(
                        f"Constraint length mismatch for {action_name} seq#{seq_idx}: "
                        f"expected {len(seq)} got {len(raw_seq_constraints)}"
                    )

                converted_seq: List[StepConstraint] = []
                for pose_label, cdict in zip(seq, raw_seq_constraints):
                    cdict = cdict or {}
                    converted_seq.append(
                        StepConstraint(
                            pose=pose_label,
                            min_duration=cdict.get("min_duration"),
                            max_duration=cdict.get("max_duration"),
                            max_gap_after_prev=cdict.get("max_gap_after_prev"),
                        )
                    )
                converted.append(converted_seq)

            step_constraints = converted

        out[action_name] = ActionDefinition(
            name=action_name,
            sequences=sequences,
            step_constraints=step_constraints,
            action_constraint=None,
        )

    return out


def build_action_families(
    action_defs: Dict[str, ActionDefinition],
    min_prefix_len: int = 2,
    min_members: int = 2,
    pretask_by_prefix: Optional[Dict[Tuple[str, ...], str]] = None,
) -> Dict[str, ActionFamily]:
    """
    Automatically build action families from shared prefixes across actions.

    A prefix qualifies as a family if:
      - length(prefix) >= min_prefix_len
      - it is shared by >= min_members actions

    pretask_by_prefix can attach a pre_task name to a family if the exact prefix tuple is present.
    """
    prefix_to_members: Dict[Tuple[str, ...], Set[str]] = {}

    for action_name, adef in action_defs.items():
        for seq in adef.sequences:
            # prefixes of length 1..len(seq) (we filter by min_prefix_len later)
            for k in range(1, len(seq) + 1):
                pref = tuple(seq[:k])
                prefix_to_members.setdefault(pref, set()).add(action_name)

    families: Dict[str, ActionFamily] = {}
    for pref, members in prefix_to_members.items():
        if len(pref) < min_prefix_len:
            continue
        if len(members) < min_members:
            continue

        family_id = "F_" + "_".join(pref)
        pre_task = None
        if pretask_by_prefix and pref in pretask_by_prefix:
            pre_task = pretask_by_prefix[pref]

        families[family_id] = ActionFamily(
            family_id=family_id,
            prefix=list(pref),
            members=set(members),
            pre_task=pre_task,
        )

    return families
