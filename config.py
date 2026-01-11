"""
Global configuration for the ontology-based HRI system (Arianna+-inspired).

This project is a *symbolic* prototype written in Python. It mirrors the
ontology-network + procedure architecture but does not require OWL tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# -----------------------
# Perception / timing
# -----------------------
POSE_TICK_SECONDS: float = 0.5  # pose detector emits one pose every 0.5s (simulation)
MAX_POSE_BUFFER_LEN: int = 50   # keep last N pose segments (compressed)

# -----------------------
# Scheduler tracing (Arianna+-style execution trace)
# -----------------------
TRACE: bool = True  # set False to disable trace output
TRACE_PAYLOAD: bool = True  # include small payload summaries in trace lines
TRACE_MAX_VALUE_LEN: int = 90  # truncate long payload values

# -----------------------
# Trace to JSON Lines (for live dashboard + evaluation)
# -----------------------
TRACE_JSONL: bool = True
TRACE_JSONL_PATH: str = "runs/trace.jsonl"
TRACE_JSONL_RESET_ON_START: bool = True  # overwrite trace file on each run

# If True, store summarized payload fields in trace records
TRACE_JSONL_INCLUDE_PAYLOAD: bool = True
TRACE_JSONL_MAX_VALUE_LEN: int = 120

# -----------------------
# Pose detector simulation mode
# -----------------------
# "random" -> random pose every tick
# "action_sequence" -> emit pose sequences that match a random action template
POSE_DETECTOR_MODE: str = "action_sequence"

# Only used when POSE_DETECTOR_MODE == "action_sequence"
STEP_DWELL_TICKS_MIN: int = 1
STEP_DWELL_TICKS_MAX: int = 4

ADD_NOISE_BETWEEN_ACTIONS: bool = False
NOISE_TICKS_MIN: int = 0
NOISE_TICKS_MAX: int = 4


# -----------------------
# Domain vocabulary
# -----------------------
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
# Keep empty -> current action set has NO time constraints.
ACTION_STEP_CONSTRAINTS: Dict[str, List[List[dict]]] = {}

# Example (COMMENT): if later you want time constraints:
# ACTION_STEP_CONSTRAINTS = {
#     "picking_objects_from_floor": [
#         [
#             {},                 # standing
#             {"min_duration": 2.0},  # picking >= 2s
#             {},                 # raising_hand
#         ]
#     ]
# }


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


# -----------------------
# Action Families + Pre-tasks 
# -----------------------
# Families are built automatically from shared prefixes.
# Here we optionally attach a "pre_task" to a prefix (tuple of pose labels).
#
# Meaning: when that prefix is observed as a suffix of the current buffer,
# the robot can do a non-committal preparation routine.
FAMILY_PRETASK_BY_PREFIX: Dict[Tuple[str, ...], str] = {
    ("sitting", "standing", "walking"): "pretask_observe_and_scan",
    ("sitting", "standing", "walking", "picking"): "pretask_scan_pick_area",
    ("standing", "picking"): "pretask_scan_floor_area",
    ("walking", "sitting"): "pretask_scan_book_area",
}

# Define what each pretask does (safe, reversible, no grasp).
PRETASK_DEFINITIONS: Dict[str, List[BehaviorStepDef]] = {
    "pretask_observe_and_scan": [
        BehaviorStepDef("face_human"),
        BehaviorStepDef("move_to_observation_point"),
        BehaviorStepDef("scan_environment"),
    ],
    "pretask_scan_pick_area": [
        BehaviorStepDef("face_human"),
        BehaviorStepDef("scan_pick_zone"),
    ],
    "pretask_scan_floor_area": [
        BehaviorStepDef("tilt_sensors_down"),
        BehaviorStepDef("scan_floor"),
    ],
    "pretask_scan_book_area": [
        BehaviorStepDef("scan_shelves_for_book"),
    ],
}


# Execution simulation
BEHAVIOR_STEP_SECONDS: float = 0.7  # each behavior step sleeps this long (simulation)
SYSTEM_NAME: str = "ontology_hri_system"
