"""Procedure U (PU): system coordination (mode + reset)."""

from __future__ import annotations

from dataclasses import dataclass

from ontologies.upper_ontology import SystemMode, UpperOntologyState
from ontologies.memory_storage import EpisodeMemory


@dataclass
class ProcedureU:
    ou_state: UpperOntologyState
    memory: EpisodeMemory

    def freeze_for_task(self) -> None:
        self.ou_state.set_mode(SystemMode.EXECUTING_TASK)

    def unfreeze_after_task(self) -> None:
        self.ou_state.set_mode(SystemMode.RECOGNIZING)

    def reset_episode(self) -> None:
        self.memory.clear()

