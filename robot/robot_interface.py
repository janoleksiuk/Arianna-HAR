"""SPOT robot interface (simulation)."""

from __future__ import annotations

from dataclasses import dataclass

from ontologies.robot_ontology import TaskDefinition
from robot.behaviors import BehaviorExecution


@dataclass
class SpotRobotSim:
    robot_id: str = "spot_sim_1"

    def execute_task(self, task: TaskDefinition, logger) -> None:
        logger.info(f"[{self.robot_id}] Starting task: {task.name}")
        for step in task.steps:
            BehaviorExecution(step.name, step.params).run(logger)
        logger.info(f"[{self.robot_id}] Completed task: {task.name}")
