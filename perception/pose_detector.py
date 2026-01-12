"""
Pose detector (simulation).

Modes controlled by config.POSE_DETECTOR_MODE:

1) "random":
   - infinite loop, emits one random pose every POSE_TICK_SECONDS.

2) "action_sequence":
   - repeatedly picks a random action and one of its template sequences,
     then emits the pose labels in that order (each step repeated for a few ticks).
   - optional noise between actions.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple, List

import config


@dataclass
class PoseDetectorSim:
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.seed is not None:
            random.seed(self.seed)

    def stream(self) -> Iterator[Tuple[str, float]]:
        mode = getattr(config, "POSE_DETECTOR_MODE", "random")
        if mode == "random":
            yield from self._stream_random()
        elif mode == "action_sequence":
            yield from self._stream_action_sequences()
        else:
            raise ValueError(f"Unknown POSE_DETECTOR_MODE: {mode!r}")

    def _tick(self, pose: str) -> Tuple[str, float]:
        t = time.time()
        time.sleep(config.POSE_TICK_SECONDS)
        return pose, t

    def _stream_random(self) -> Iterator[Tuple[str, float]]:
        poses = sorted(list(config.POSE_SET))
        while True:
            pose = random.choice(poses)
            yield self._tick(pose)

    def _stream_action_sequences(self) -> Iterator[Tuple[str, float]]:
        poses_all = sorted(list(config.POSE_SET))
        action_names = list(config.ACTION_DEFINITIONS.keys())

        dwell_min = getattr(config, "STEP_DWELL_TICKS_MIN", 1)
        dwell_max = getattr(config, "STEP_DWELL_TICKS_MAX", 4)

        add_noise = getattr(config, "ADD_NOISE_BETWEEN_ACTIONS", True)
        noise_min = getattr(config, "NOISE_TICKS_MIN", 0)
        noise_max = getattr(config, "NOISE_TICKS_MAX", 4)

        if not action_names:
            raise ValueError("No actions in config.ACTION_DEFINITIONS to generate sequences from.")

        while True:
            # Choose random action and one of its sequences
            action = random.choice(action_names)
            sequences: List[List[str]] = config.ACTION_DEFINITIONS[action]
            seq = random.choice(sequences)

            # Emit the action sequence with dwell (repeats)
            for pose_label in seq:
                repeats = random.randint(dwell_min, dwell_max)
                for _ in range(repeats):
                    yield self._tick(pose_label)

