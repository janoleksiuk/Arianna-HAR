"""
Global configuration for the ontology-based HRI system (Arianna+-inspired).

This project is a *symbolic* prototype written in Python. It mirrors the
ontology-network + procedure architecture but does not require OWL tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


# -----------------------
# Perception / timing
# -----------------------
POSE_TICK_SECONDS: float = 0.5  # pose detector emits one pose every 0.5s (simulation)
MAX_POSE_BUFFER_LEN: int = 50   # keep last N pose segments (compressed)

# -----------------------
# Pose detector simulation mode
# -----------------------
# "random" -> random pose every tick
# "action_sequence" -> emit pose sequences that match a random action template
POSE_DETECTOR_MODE: str = "action_sequence"

# Only used when POSE_DETECTOR_MODE == "action_sequence"
# How many ticks to repeat each pose step (repetition creates pose "duration" in compressed segments)
STEP_DWELL_TICKS_MIN: int = 1
STEP_DWELL_TICKS_MAX: int = 4

# -----------------------
# Domain vocabulary
# -----------------------
# Pose labels (finite set) as requested:
# {(sitting, standing, raising hand, picking, bowing, walking, drinking)}
POSE_SET = {
    "sitting",
    "standing",
    "raising_hand",
    "picking",
    "bowing",
    "walking",
    "drinking",
}


# -----------------------
# Action definitions (NO time constraints used here)
# -----------------------
ACTION_DEFINITIONS: Dict[str, List[List[str]]] = {
    "drinking_water": [
        ["sitting", "standing", "walking", "picking", "walking", "sitting"],
    ],
    "requesting_for_a_book": [
        ["walking", "sitting", "raising_hand"],
    ],
    "waste_disposal": [
        ["sitting", "standing", "walking", "picking", "walking", "sitting", "drinking"],
    ],
    "picking_objects_from_floor": [
        ["standing", "picking", "raising_hand"],
    ],
    "washing_hands": [
        ["sitting", "standing", "walking", "bowing"],
    ],
}

# Optional (currently unused): step constraints per action sequence.
# Keep this empty to ensure the current action set has NO time constraints.
#
# Structure:
# ACTION_STEP_CONSTRAINTS[action_name] = [
#   [  # constraints for sequence #0 (same length as ACTION_DEFINITIONS[action_name][0])
#     {"min_duration": None, "max_duration": None, "max_gap_after_prev": None},
#     ...
#   ],
#   ... sequence #1 constraints, etc.
# ]
ACTION_STEP_CONSTRAINTS: Dict[str, List[List[dict]]] = {}

# Example (COMMENTED OUT): If you later want time constraints, you could do:
#
# ACTION_STEP_CONSTRAINTS = {
#     "requesting_for_a_book": [
#         [
#             {},                 # standing (no constraint)
#             {"min_duration": 1.0},  # picking must last >= 1 seconds
#             {},                 # raising_hand
#         ]
#     ]
# }
#
# With POSE_TICK_SECONDS=0.5, min_duration=2.0 requires ~4 consecutive picking ticks.


# -----------------------
# Tasks (one per action)
# -----------------------
ACTION_TO_TASK: Dict[str, str] = {
    "drinking_water": "localise_and_deliver_bottle_of_water",
    "requesting_for_a_book": "localise_and_deliver_book",
    "waste_disposal": "approach_collect_and_bin_can",
    "picking_objects_from_floor": "localise_and_deliver_object_from_floor",
    "washing_hands": "localise_and_deliver_sponge",
}


@dataclass(frozen=True)
class BehaviorStepDef:
    """A simple behavior step definition used by the task ontology."""
    name: str
    params: Optional[Dict[str, str]] = None


TASK_DEFINITIONS: Dict[str, List[BehaviorStepDef]] = {
    "localise_and_deliver_bottle_of_water": [
        BehaviorStepDef("search_object", {"object": "bottle_of_water"}),
        BehaviorStepDef("approach_object", {"object": "bottle_of_water"}),
        BehaviorStepDef("grasp_object", {"object": "bottle_of_water"}),
        BehaviorStepDef("search_object", {"object": "human"}),
        BehaviorStepDef("approach_object", {"object": "human"}),
        BehaviorStepDef("release_object", {"object": "bottle_of_water"}),
        BehaviorStepDef("return_to_start"),
    ],
    "localise_and_deliver_book": [
        BehaviorStepDef("search_object", {"object": "book"}),
        BehaviorStepDef("approach_object", {"object": "book"}),
        BehaviorStepDef("grasp_object", {"object": "book"}),
        BehaviorStepDef("search_object", {"object": "human"}),
        BehaviorStepDef("approach_object", {"object": "human"}),
        BehaviorStepDef("release_object", {"object": "book"}),
        BehaviorStepDef("return_to_start"),
    ],
    "approach_collect_and_bin_can": [
        BehaviorStepDef("search_object", {"object": "human"}),
        BehaviorStepDef("approach_object", {"object": "human"}),
        BehaviorStepDef("collect_object", {"object": "empty_can"}),
        BehaviorStepDef("navigate_to", {"location": "bin"}),
        BehaviorStepDef("drop_object", {"object": "empty_can"}),
        BehaviorStepDef("return_to_start"),
    ],
    "localise_and_deliver_object_from_floor": [
        BehaviorStepDef("search_object", {"object": "object_on_floor"}),
        BehaviorStepDef("approach_object", {"object": "object_on_floor"}),
        BehaviorStepDef("grasp_object", {"object": "object_on_floor"}),
        BehaviorStepDef("search_object", {"object": "human"}),
        BehaviorStepDef("approach_object", {"object": "human"}),
        BehaviorStepDef("release_object", {"object": "object_on_floor"}),
        BehaviorStepDef("return_to_start"),
    ],
    "localise_and_deliver_sponge": [
        BehaviorStepDef("search_object", {"object": "sponge"}),
        BehaviorStepDef("approach_object", {"object": "sponge"}),
        BehaviorStepDef("grasp_object", {"object": "sponge"}),
        BehaviorStepDef("search_object", {"object": "human"}),
        BehaviorStepDef("approach_object", {"object": "human"}),
        BehaviorStepDef("release_object", {"object": "sponge"}),
        BehaviorStepDef("return_to_start"),
    ],
}


# Execution simulation
BEHAVIOR_STEP_SECONDS: float = 0.7  # each behavior step sleeps this long (simulation)
SYSTEM_NAME: str = "ontology_hri_system"
