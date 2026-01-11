"""Robot behavior primitives (simulation)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

from config import BEHAVIOR_STEP_SECONDS


@dataclass(frozen=True)
class BehaviorExecution:
    name: str
    params: Optional[Dict[str, str]] = None

    def run(self, logger) -> None:
        if self.params:
            logger.info(f"  - Behavior: {self.name} | params={self.params}")
        else:
            logger.info(f"  - Behavior: {self.name}")
        time.sleep(BEHAVIOR_STEP_SECONDS)
