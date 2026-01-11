"""
Procedure R (PR): action → task dispatch + early preparation.

New:
- prepare_family(): starts a pre-task in a background thread (non-blocking).
- cancel_pretask(): cancels and optionally waits for completion.
- dispatch(): cancels pre-task first, then executes final task synchronously.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import threading

from ontologies.human_action_ontology import ActionInstance, ActionFamily
from ontologies.robot_ontology import TaskDefinition
from ontologies.memory_storage import EpisodeMemory
from config import ACTION_TO_TASK
from robot.robot_interface import SpotRobotSim


@dataclass
class ProcedureR:
    tasks: Dict[str, TaskDefinition]
    pretasks: Dict[str, TaskDefinition]
    robot: SpotRobotSim
    memory: EpisodeMemory

    current_prepared_family_id: Optional[str] = None

    # Threading state
    _pretask_thread: Optional[threading.Thread] = None
    _pretask_stop_event: threading.Event = threading.Event()
    _lock: threading.Lock = threading.Lock()

    def _pretask_worker(self, task_def: TaskDefinition, logger) -> None:
        """Run pretask in background with cancellation support."""
        self.robot.execute_task(task_def, logger, stop_event=self._pretask_stop_event)

    def cancel_pretask(self, logger=None, join: bool = False) -> None:
        """Request cancellation of pre-task; optionally wait for thread exit."""
        with self._lock:
            th = self._pretask_thread
            if th is None:
                return

            self._pretask_stop_event.set()

        if join and th.is_alive():
            th.join(timeout=5.0)

        with self._lock:
            # If thread ended, clean up
            if self._pretask_thread is not None and not self._pretask_thread.is_alive():
                self._pretask_thread = None
            # Keep prepared_family_id as-is; it will change on next prepare

    def prepare_family(self, family: ActionFamily, logger) -> None:
        """
        Start a non-committal preparation routine in another thread if configured.
        Returns immediately (does not block pose detection).
        """
        if family.pre_task is None:
            return

        # If we are already prepared for this family and a pretask thread is running, do nothing
        with self._lock:
            if self.current_prepared_family_id == family.family_id:
                # If thread is alive, we are already preparing/prepared
                if self._pretask_thread is not None and self._pretask_thread.is_alive():
                    return
                # If thread is not alive, we already prepared earlier; also do nothing
                return

        # New family: cancel any existing pretask and start a new one
        self.cancel_pretask(logger=logger, join=True)

        pretask_name = family.pre_task
        task_def = self.pretasks.get(pretask_name)
        if task_def is None:
            logger.warning(f"Pre-task {pretask_name!r} not found for family {family.family_id}")
            with self._lock:
                self.current_prepared_family_id = family.family_id
            return

        logger.info(f"[PREP-ASYNC] Family={family.family_id} prefix={family.prefix} -> pre_task={pretask_name}")

        with self._lock:
            self._pretask_stop_event = threading.Event()  # fresh event per run
            self.current_prepared_family_id = family.family_id
            self._pretask_thread = threading.Thread(
                target=self._pretask_worker,
                args=(task_def, logger),
                daemon=True,
            )
            self._pretask_thread.start()

    def clear_preparation(self) -> None:
        with self._lock:
            self.current_prepared_family_id = None

    def dispatch(self, action_inst: ActionInstance, logger) -> str:
        """
        Commit to a final task.
        We cancel any running pre-task first to avoid robot concurrency conflicts.
        """
        # Stop pretask immediately and wait for it to exit
        self.cancel_pretask(logger=logger, join=True)
        self.clear_preparation()

        task_name = ACTION_TO_TASK.get(action_inst.name)
        if task_name is None:
            raise ValueError(f"No task mapping for action: {action_inst.name}")

        task_def = self.tasks[task_name]
        logger.info(f"Action recognized: {action_inst.name} | Dispatching task: {task_name}")

        # Final task runs synchronously (unchanged baseline)
        self.robot.execute_task(task_def, logger)
        self.memory.executed_tasks.append(task_name)
        return task_name
