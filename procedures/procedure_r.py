"""
Procedure R (PR): action → task dispatch + early preparation (multi-human).

- Pre-task runs in another thread (does not block pose detection).
- Final dispatch cancels any running pre-task, then runs final task synchronously.
- Executed tasks are recorded per human_id.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import threading

from ontologies.human_action_ontology import ActionInstance, ActionFamily
from ontologies.robot_ontology import TaskDefinition
from ontologies.memory_storage import MultiHumanMemoryStore
from config import ACTION_TO_TASK
from robot.robot_interface import SpotRobotSim


@dataclass
class ProcedureR:
    tasks: Dict[str, TaskDefinition]
    pretasks: Dict[str, TaskDefinition]
    robot: SpotRobotSim
    memory_store: MultiHumanMemoryStore

    # which (human, family) we prepared for
    current_prepared: Optional[Tuple[str, str]] = None

    _pretask_thread: Optional[threading.Thread] = None
    _pretask_stop_event: threading.Event = threading.Event()
    _lock: threading.Lock = threading.Lock()

    def _pretask_worker(self, task_def: TaskDefinition, logger) -> None:
        self.robot.execute_task(task_def, logger, stop_event=self._pretask_stop_event)

    def cancel_pretask(self, join: bool = False) -> None:
        with self._lock:
            th = self._pretask_thread
            if th is None:
                return
            self._pretask_stop_event.set()

        if join and th.is_alive():
            th.join(timeout=5.0)

        with self._lock:
            if self._pretask_thread is not None and not self._pretask_thread.is_alive():
                self._pretask_thread = None

    def prepare_family(self, human_id: str, family: ActionFamily, logger) -> None:
        """Start a non-committal preparation routine (async) if configured for this family."""
        if family.pre_task is None:
            return

        with self._lock:
            if self.current_prepared == (human_id, family.family_id):
                if self._pretask_thread is not None and self._pretask_thread.is_alive():
                    return
                return

        # new target: cancel old pretask and start new one
        self.cancel_pretask(join=True)

        pretask_name = family.pre_task
        task_def = self.pretasks.get(pretask_name)
        if task_def is None:
            logger.warning(f"Pre-task {pretask_name!r} not found for family {family.family_id}")
            with self._lock:
                self.current_prepared = (human_id, family.family_id)
            return

        logger.info(f"[PREP-ASYNC] human={human_id} family={family.family_id} prefix={family.prefix} -> {pretask_name}")

        with self._lock:
            self._pretask_stop_event = threading.Event()
            self.current_prepared = (human_id, family.family_id)
            self._pretask_thread = threading.Thread(
                target=self._pretask_worker,
                args=(task_def, logger),
                daemon=True,
            )
            self._pretask_thread.start()

    def dispatch(self, human_id: str, action_inst: ActionInstance, logger) -> str:
        """Commit to a final task for a given human."""
        self.cancel_pretask(join=True)
        with self._lock:
            self.current_prepared = None

        task_name = ACTION_TO_TASK.get(action_inst.name)
        if task_name is None:
            raise ValueError(f"No task mapping for action: {action_inst.name}")

        task_def = self.tasks[task_name]
        logger.info(f"Action recognized (human={human_id}): {action_inst.name} | Dispatching task: {task_name}")

        self.robot.execute_task(task_def, logger)

        memory = self.memory_store.get(human_id)
        memory.executed_tasks.append(task_name)
        return task_name
