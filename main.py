"""
Main entry point.

PoseDetector -> ProcedureP (pose segments) -> ProcedureS (human state)
-> ProcedureA (action recognition) -> ProcedureR (robot task execution)

Recognition is paused during task execution by synchronous task execution.
After each task completes, memory is cleared to begin a new episode.
"""

from __future__ import annotations

import logging

import config
from utils.logger import setup_logger

from ontologies.upper_ontology import UpperOntologyState, SystemMode
from ontologies.human_state_ontology import HumanState
from ontologies.human_action_ontology import build_action_definitions
from ontologies.robot_ontology import build_task_definitions
from ontologies.memory_storage import EpisodeMemory

from procedures.procedure_u import ProcedureU
from procedures.procedure_p import ProcedureP
from procedures.procedure_s import ProcedureS
from procedures.procedure_a import ProcedureA
from procedures.procedure_r import ProcedureR

from perception.pose_detector import PoseDetectorSim
from robot.robot_interface import SpotRobotSim


def main() -> None:
    logger = setup_logger(logging.INFO)
    logger.info(f"Starting {config.SYSTEM_NAME} ...")
    logger.info(f"Pose set: {sorted(list(config.POSE_SET))}")
    logger.info(f"Actions: {list(config.ACTION_DEFINITIONS.keys())}")

    # Ontology-like state objects
    ou_state = UpperOntologyState()
    human_state = HumanState()
    memory = EpisodeMemory()

    # Build definitions (constraints supported but empty by default)
    action_defs = build_action_definitions(
        config.ACTION_DEFINITIONS,
        step_constraints_dict=getattr(config, "ACTION_STEP_CONSTRAINTS", None),
    )
    task_defs = build_task_definitions(config.TASK_DEFINITIONS)

    # Robot
    robot = SpotRobotSim(robot_id="spot_sim_1")

    # Procedures
    pu = ProcedureU(ou_state=ou_state, memory=memory)
    pp = ProcedureP(memory=memory)
    ps = ProcedureS(human_state=human_state)
    pa = ProcedureA(action_defs=action_defs, memory=memory)
    pr = ProcedureR(tasks=task_defs, robot=robot, memory=memory)

    # Pose detector
    detector = PoseDetectorSim(seed=None)
    stream = detector.stream()

    logger.info("Entering main loop (Ctrl+C to stop) ...")
    try:
        for pose_label, t in stream:
            if ou_state.mode != SystemMode.RECOGNIZING:
                continue

            # Ingest pose
            pose_stmt = pp.ingest_pose_label(pose_label, t=t)
            ps.update_from_pose_statement(pose_stmt)

            logger.info(f"Observed pose: {pose_stmt.label} | buffer_len={len(memory.pose_segments)}")
            pa.debug_print_candidates(logger)

            # Attempt action recognition
            action_inst = pa.detect_action(now_t=t)
            if action_inst is not None:
                pu.freeze_for_task()
                task_name = pr.dispatch(action_inst, logger)

                pu.reset_episode()
                pu.unfreeze_after_task()
                logger.info(f"System reset; ready for next episode. (last_task={task_name})")

    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt).")


if __name__ == "__main__":
    main()
