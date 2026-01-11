"""
Main entry point using an event-based scheduler (Arianna+-style).

Pipeline becomes explicit via events:

PoseTick
  -> PoseSegmentUpdated
    -> HumanStateUpdated
    -> EarlyIntentUpdated (and maybe BestFamilyChanged)
    -> ActionRecognized
      -> TaskCompleted
"""

from __future__ import annotations

import logging

import config
from utils.logger import setup_logger

from scheduler import EventScheduler, make_condition, make_procedure

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

    # -----------------------
    # Instantiate ontologies / memory
    # -----------------------
    ou_state = UpperOntologyState()
    memory_store = MultiHumanMemoryStore()
    human_states: dict[str, HumanState] = {}

    # Action defs + families
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

    # Tasks + pretasks
    task_defs = build_task_definitions(config.TASK_DEFINITIONS)
    pretask_defs = build_task_definitions(config.PRETASK_DEFINITIONS)

    # Robot
    robot = SpotRobotSim(robot_id="spot_sim_1")

    # Procedures
    pu = ProcedureU(ou_state=ou_state, memory_store=memory_store)
    pp = ProcedureP(memory_store=memory_store)
    ps = ProcedureS(human_states=human_states)
    pa = ProcedureA(action_defs=action_defs, memory_store=memory_store, families=families)
    pr = ProcedureR(tasks=task_defs, pretasks=pretask_defs, robot=robot, memory_store=memory_store)

    # -----------------------
    # Scheduler + shared state (blackboard)
    # -----------------------
    sched = EventScheduler(
        state={
            "logger": logger,
            "ou_state": ou_state,
            "families": families,
            "last_best_family_id": {},
            "tick_action_recognized": {},
        },
        trace=getattr(config, "TRACE", False),
        trace_payload=getattr(config, "TRACE_PAYLOAD", False),
        trace_max_value_len=getattr(config, "TRACE_MAX_VALUE_LEN", 90),
    )


    # -----------------------
    # Conditions
    # -----------------------
    def is_recognizing(s: EventScheduler, e) -> bool:
        return s.state["ou_state"].mode == SystemMode.RECOGNIZING

    cond_recognizing = make_condition("mode_is_recognizing", is_recognizing)

    # -----------------------
    # Event-driven procedures
    # -----------------------

    # (0) Reset tick flags (runs first on PoseTick)
    def proc_reset_tick(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]
        s.state["tick_action_recognized"][hid] = False

    sched.register("PoseTick", make_procedure("ResetTickFlags", proc_reset_tick))

    # (1) Perception -> PoseSegmentUpdated
    def proc_perception_to_pose(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]
        pose = e.payload["pose_label"]
        t = e.payload["t"]
        pose_stmt = pp.ingest_pose_label(pose, human_id=hid, t=t)
        s.emit("PoseSegmentUpdated", {"human_id": hid, "pose_stmt": pose_stmt}, t=t)

    sched.register("PoseTick", make_procedure("PerceptionToPoseSegment", proc_perception_to_pose))

    # (2) Update human state (OS)
    def proc_update_human_state(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]
        pose_stmt = e.payload["pose_stmt"]
        ps.update_from_pose_statement(pose_stmt, human_id=hid)
        s.emit("HumanStateUpdated", {"human_id": hid}, t=e.t)

    sched.register("PoseSegmentUpdated", make_procedure("UpdateHumanState", proc_update_human_state))

    # (3) Detect final action (OA) -> ActionRecognized
    def proc_detect_action(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]
        action_inst = pa.detect_action(human_id=hid, now_t=e.t)
        if action_inst is not None:
            s.state["tick_action_recognized"][hid] = True
            s.emit("ActionRecognized", {"human_id": hid, "action_inst": action_inst}, t=e.t)

    sched.register("PoseSegmentUpdated", make_procedure("DetectAction", proc_detect_action, [cond_recognizing]))

    # (4) Early intent / family update (OA) -> BestFamilyChanged
    def proc_early_intent(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]

        # Avoid starting prep if we already recognized an action on this same tick
        if s.state["tick_action_recognized"].get(hid, False):
            return

        intent = pa.compute_early_intent(human_id=hid)
        s.emit("EarlyIntentUpdated", {"human_id": hid, "intent": intent}, t=e.t)

        best = intent.best_family_id
        last_map: dict = s.state["last_best_family_id"]
        last = last_map.get(hid)

        if best is not None and best != last:
            last_map[hid] = best
            s.emit("BestFamilyChanged", {"human_id": hid, "family_id": best}, t=e.t)

    sched.register("PoseSegmentUpdated", make_procedure("ComputeEarlyIntent", proc_early_intent, [cond_recognizing]))

    # (5) Prepare family (OR): async pre-task
    def proc_prepare_family(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]
        fam_id = e.payload["family_id"]
        fam = families[fam_id]
        pr.prepare_family(human_id=hid, family=fam, logger=logger)

    sched.register("BestFamilyChanged", make_procedure("PrepareFamilyPretask", proc_prepare_family, [cond_recognizing]))

    # (6) Dispatch final task (OR) + emit TaskCompleted
    def proc_dispatch_task(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]
        action_inst = e.payload["action_inst"]

        pu.freeze_for_task()
        task_name = pr.dispatch(human_id=hid, action_inst=action_inst, logger=logger)
        s.emit("TaskCompleted", {"human_id": hid, "task_name": task_name}, t=e.t)

    sched.register("ActionRecognized", make_procedure("DispatchTask", proc_dispatch_task, [cond_recognizing]))

    # (7) On task completion: reset per human + unfreeze
    def proc_on_task_completed(s: EventScheduler, e) -> None:
        hid = e.payload["human_id"]
        pu.reset_episode(human_id=hid)
        pu.unfreeze_after_task()

        # reset best family memory for that human
        s.state["last_best_family_id"][hid] = None

        logger.info(f"[{hid}] System reset; ready for next episode. (last_task={e.payload['task_name']})")

    sched.register("TaskCompleted", make_procedure("OnTaskCompleted", proc_on_task_completed))

    # -----------------------
    # Pose detector loop -> emits PoseTick events
    # -----------------------
    detector = PoseDetectorSim(seed=None)
    stream = detector.stream()

    logger.info("Entering event-driven loop (Ctrl+C to stop) ...")
    try:
        for pose_label, t in stream:
            # still simulating one human
            human_id = "human_1"

            sched.emit("PoseTick", {"human_id": human_id, "pose_label": pose_label, "t": t}, t=t)
            sched.run_until_idle(max_events=1000)

    except KeyboardInterrupt:
        logger.info("Shutting down (KeyboardInterrupt).")


if __name__ == "__main__":
    main()
