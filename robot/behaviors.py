"""Robot behavior primitives (simulation) with cooperative cancellation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional
import threading

from config import BEHAVIOR_STEP_SECONDS


@dataclass(frozen=True)
class BehaviorExecution:
    name: str
    params: Optional[Dict[str, str]] = None

    def run(self, logger, stop_event: Optional[threading.Event] = None) -> bool:
        """
        Run the behavior step.
        Returns True if completed, False if cancelled.

        Cancellation is cooperative: we check stop_event periodically during sleep.
        """
        if stop_event is not None and stop_event.is_set():
            logger.info(f"  - Behavior cancelled before start: {self.name}")
            return False

        if self.params:
            logger.info(f"  - Behavior: {self.name} | params={self.params}")
        else:
            logger.info(f"  - Behavior: {self.name}")

        # Sleep in small increments so cancellation is responsive
        remaining = BEHAVIOR_STEP_SECONDS
        tick = 0.05
        while remaining > 0:
            if stop_event is not None and stop_event.is_set():
                logger.info(f"  - Behavior cancelled mid-step: {self.name}")
                return False
            dt = min(tick, remaining)
            time.sleep(dt)
            remaining -= dt

        return True
