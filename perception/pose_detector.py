"""Pose detector (simulation).

In infinite loop it outputs one random recognized pose every 0.5 second.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from config import POSE_SET, POSE_TICK_SECONDS


@dataclass
class PoseDetectorSim:
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        if self.seed is not None:
            random.seed(self.seed)

    def stream(self) -> Iterator[Tuple[str, float]]:
        """Yield (pose_label, timestamp) forever."""
        poses = sorted(list(POSE_SET))
        while True:
            pose = random.choice(poses)
            t = time.time()
            yield pose, t
            time.sleep(POSE_TICK_SECONDS)

