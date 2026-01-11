"""
Main entry point.

Now includes early intent + family preparation:
- compute_early_intent() returns best family
- if best family changes, ProcedureR.prepare_family() runs a pre-task

Final action detection still triggers full task dispatch as before.
"""

from __future__ import annotations

import logging

import config
from utils.logger import setup_logger

from ontologies.upper_ontology import UpperOntologyState, SystemMode
from ontologies.human_state_ontology import HumanState
from ontologies.human_action_ontology import build_action_definitions, build_action_families
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

    # Build action definitions (constraints supported but empty by default)
    action_defs = build_action_definitions(
        config.ACTION_DEFINITIONS,
        step_constraints_dict=getattr(config, "ACTION_STEP_CONSTRAINTS", None),
    )

    # Build families automatically + attach pretasks by prefix
    families = build_action_families(
        action_defs,
        min_prefix_len=2,
        min_members=2,
        pretask_by_prefix=getattr(config, "FAMILY_PRETASK_BY_PREFIX", None),
    )
    logger.info(f"Built {len(families)} action families (shared prefixes).")

    # Build tasks and pretasks
    task_defs = build_task_definitions(config.TASK_DEFINITIONS)
    pretask_defs = build_task_definitions(config.PRETASK_DEFINITIONS)

    # Robot
    robot = SpotRobotSim(robot_id="spot_sim_1")

    # Procedures
    pu = ProcedureU(ou_state=ou_state, memory=memory)
    pp = ProcedureP(memory=memory)
    ps = ProcedureS(human_state=human_state)
    pa = ProcedureA(action_defs=action_defs, memory=memory, families=families)
    pr = ProcedureR(tasks=task_defs, pretasks=pretask_defs, robot=robot, memory=memory)

    # Pose detector
    detector = PoseDetectorSim(seed=None)
    stream = detector.stream()

    logger.info("Entering main loop (Ctrl+C to stop) ...")
    last_best_family_id = None

    try:
        for pose_label, t in stream:
            if ou_state.mode != SystemMode.RECOGNIZING:
                continue

            # Ingest pose
            pose_stmt = pp.ingest_pose_label(pose_label, t=t)
            ps.update_from_pose_statement(pose_stmt)
            logger.info(f"Observed pose: {pose_stmt.label} | buffer_len={len(memory.pose_segments)}")

            # Early intent (families)
            intent = pa.compute_early_intent()
            if intent.best_family_id is not None and intent.best_family_id != last_best_family_id:
                fam = families[intent.best_family_id]
                pr.prepare_family(fam, logger)
                last_best_family_id = intent.best_family_id

            # Final recognition
            action_inst = pa.detect_action(now_t=t)
            if action_inst is not None:
                pu.freeze_for_task()
                task_name = pr.dispatch(action_inst, logger)

                # Keep your current behavior: reset episode after task.
                pu.reset_episode()
                pu.unfreeze_after_task()
                last_best_family_id = None
                pr.clear_preparation()

                logger.info(f"System reset; ready for next episode. (last_task={task_name})")

    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt).")


if __name__ == "__main__":
    main()
