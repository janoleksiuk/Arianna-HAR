"""
Main entry point (multi-human ready).

We still simulate only one person: human_id = "human_1"
But all procedures and memory/state are per-human.
"""

from __future__ import annotations

import logging

import config
from utils.logger import setup_logger

from ontologies.upper_ontology import UpperOntologyState, SystemMode
from ontologies.human_state_ontology import HumanState
from ontologies.human_action_ontology import build_action_definitions, build_action_families
from ontologies.robot_ontology import build_task_definitions
from ontologies.memory_storage import MultiHumanMemoryStore

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

    # Global coordination (one robot)
    ou_state = UpperOntologyState()

    # Multi-human stores
    memory_store = MultiHumanMemoryStore()
    human_states: dict[str, HumanState] = {}

    # Build definitions
    action_defs = build_action_definitions(
        config.ACTION_DEFINITIONS,
        step_constraints_dict=getattr(config, "ACTION_STEP_CONSTRAINTS", None),
    )

    families = build_action_families(
        action_defs,
        min_prefix_len=2,
        min_members=2,
        pretask_by_prefix=getattr(config, "FAMILY_PRETASK_BY_PREFIX", None),
    )
    logger.info(f"Built {len(families)} action families (shared prefixes).")

    task_defs = build_task_definitions(config.TASK_DEFINITIONS)
    pretask_defs = build_task_definitions(config.PRETASK_DEFINITIONS)

    robot = SpotRobotSim(robot_id="spot_sim_1")

    # Procedures (multi-human)
    pu = ProcedureU(ou_state=ou_state, memory_store=memory_store)
    pp = ProcedureP(memory_store=memory_store)
    ps = ProcedureS(human_states=human_states)
    pa = ProcedureA(action_defs=action_defs, memory_store=memory_store, families=families)
    pr = ProcedureR(tasks=task_defs, pretasks=pretask_defs, robot=robot, memory_store=memory_store)

    detector = PoseDetectorSim(seed=None)
    stream = detector.stream()

    logger.info("Entering main loop (Ctrl+C to stop) ...")

    # We keep last best family per human
    last_best_family_id: dict[str, str | None] = {}

    try:
        for pose_label, t in stream:
            # Still simulating one person:
            human_id = "human_1"

            if ou_state.mode != SystemMode.RECOGNIZING:
                continue

            # Ingest pose into the human-specific buffer
            pose_stmt = pp.ingest_pose_label(pose_label, human_id=human_id, t=t)
            ps.update_from_pose_statement(pose_stmt, human_id=human_id)
            logger.info(f"[{human_id}] Observed pose: {pose_stmt.label}")

            # Early intent per human
            intent = pa.compute_early_intent(human_id=human_id)
            prev = last_best_family_id.get(human_id)

            if intent.best_family_id is not None and intent.best_family_id != prev:
                fam = families[intent.best_family_id]
                pr.prepare_family(human_id=human_id, family=fam, logger=logger)
                last_best_family_id[human_id] = intent.best_family_id

            # Final recognition per human
            action_inst = pa.detect_action(human_id=human_id, now_t=t)
            if action_inst is not None:
                pu.freeze_for_task()
                task_name = pr.dispatch(human_id=human_id, action_inst=action_inst, logger=logger)

                # Keep existing behavior: after task, reset that human's episode
                pu.reset_episode(human_id=human_id)
                pu.unfreeze_after_task()
                last_best_family_id[human_id] = None

                logger.info(f"[{human_id}] System reset; ready for next episode. (last_task={task_name})")

    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt).")


if __name__ == "__main__":
    main()
