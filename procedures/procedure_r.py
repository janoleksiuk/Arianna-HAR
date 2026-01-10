"""Procedure R (PR): action → task dispatch and execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ontologies.human_action_ontology import ActionInstance
from ontologies.robot_ontology import TaskDefinition
from ontologies.memory_storage import EpisodeMemory
from config import ACTION_TO_TASK
from robot.robot_interface import SpotRobotSim


@dataclass
class ProcedureR:
    tasks: Dict[str, TaskDefinition]
    robot: SpotRobotSim
    memory: EpisodeMemory

    def dispatch(self, action_inst: ActionInstance, logger) -> str:
        task_name = ACTION_TO_TASK.get(action_inst.name)
        if task_name is None:
            raise ValueError(f"No task mapping for action: {action_inst.name}")

        task_def = self.tasks[task_name]
        logger.info(f"Action recognized: {action_inst.name} | Dispatching task: {task_name}")

        self.robot.execute_task(task_def, logger)
        self.memory.executed_tasks.append(task_name)
        return task_name

