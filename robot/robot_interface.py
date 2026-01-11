"""SPOT robot interface (simulation).

Now supports cooperative cancellation via stop_event.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import threading

from ontologies.robot_ontology import TaskDefinition
from robot.behaviors import BehaviorExecution


@dataclass
class SpotRobotSim:
    robot_id: str = "spot_sim_1"

    def execute_task(
        self,
        task: TaskDefinition,
        logger,
        stop_event: Optional[threading.Event] = None,
    ) -> None:
        logger.info(f"[{self.robot_id}] Starting task: {task.name}")

        for step in task.steps:
            if stop_event is not None and stop_event.is_set():
                logger.info(f"[{self.robot_id}] Task cancelled: {task.name}")
                return

            ok = BehaviorExecution(step.name, step.params).run(logger, stop_event=stop_event)
            if not ok:
                logger.info(f"[{self.robot_id}] Task cancelled during step: {task.name}")
                return

        logger.info(f"[{self.robot_id}] Completed task: {task.name}")
