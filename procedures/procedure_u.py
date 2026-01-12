"""Procedure U (PU): system coordination (multi-human).

Freeze/unfreeze remains global (one robot).
Reset is per-human.
"""

from __future__ import annotations

from dataclasses import dataclass

from ontologies.upper_ontology import SystemMode, UpperOntologyState
from ontologies.memory_storage import MultiHumanMemoryStore


@dataclass
class ProcedureU:
    ou_state: UpperOntologyState
    memory_store: MultiHumanMemoryStore

    def freeze_for_task(self) -> None:
        self.ou_state.set_mode(SystemMode.EXECUTING_TASK)

    def unfreeze_after_task(self) -> None:
        self.ou_state.set_mode(SystemMode.RECOGNIZING)

    def reset_episode(self, human_id: str) -> None:
        """Clear accumulated pose segments and action/task history for a given human."""
        self.memory_store.clear_human(human_id)
