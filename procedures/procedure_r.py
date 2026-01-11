"""
Procedure R (PR): action → task dispatch + early preparation.

New:
- prepare_family(): run a pre-task for the currently best family (non-committal)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

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

    def prepare_family(self, family: ActionFamily, logger) -> None:
        """
        Run a non-committal preparation routine if configured for this family.
        It is executed only once per family switch to avoid repeated triggering.
        """
        if family.pre_task is None:
            return

        if self.current_prepared_family_id == family.family_id:
            return  # already prepared for this family

        pretask_name = family.pre_task
        task_def = self.pretasks.get(pretask_name)
        if task_def is None:
            logger.warning(f"Pre-task {pretask_name!r} not found for family {family.family_id}")
            self.current_prepared_family_id = family.family_id
            return

        logger.info(f"[PREP] Family={family.family_id} prefix={family.prefix} -> pre_task={pretask_name}")
        self.robot.execute_task(task_def, logger)

        self.current_prepared_family_id = family.family_id

    def clear_preparation(self) -> None:
        self.current_prepared_family_id = None

    def dispatch(self, action_inst: ActionInstance, logger) -> str:
        # Once we commit to a final task, clear preparation state.
        self.clear_preparation()

        task_name = ACTION_TO_TASK.get(action_inst.name)
        if task_name is None:
            raise ValueError(f"No task mapping for action: {action_inst.name}")

        task_def = self.tasks[task_name]
        logger.info(f"Action recognized: {action_inst.name} | Dispatching task: {task_name}")

        self.robot.execute_task(task_def, logger)
        self.memory.executed_tasks.append(task_name)
        return task_name
