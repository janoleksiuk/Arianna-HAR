"""Perception Ontology (OP) - pose statements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PoseStatement:
    """A pose segment: label from start_time to end_time."""
    label: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    def extend_to(self, new_end_time: float) -> None:
        if new_end_time > self.end_time:
            self.end_time = new_end_time

