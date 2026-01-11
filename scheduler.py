"""
A small event-based scheduler (Arianna+-style) + JSONL trace export.

Trace records include:
- emit events
- dispatch events
- run procedures
- register calls (optional)
- cycle_id (increments on PoseTick) to group one tick chain

This is intentionally minimal and deterministic.
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

from ontologies.upper_ontology import RuntimeEvent, Procedure, Condition


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: max(0, n - 1)] + "…"


def _summarize_value(v: Any, max_len: int) -> str:
    # common objects in this project
    if hasattr(v, "label") and hasattr(v, "start_time") and hasattr(v, "end_time"):
        return f"{v.__class__.__name__}(label={getattr(v, 'label', None)})"
    if hasattr(v, "name") and hasattr(v, "matched_sequence"):
        return f"{v.__class__.__name__}(name={getattr(v, 'name', None)})"
    if isinstance(v, (int, float, bool, type(None))):
        return str(v)
    if isinstance(v, str):
        return _truncate(v, max_len)
    if isinstance(v, list):
        return _truncate(repr(v), max_len)
    if isinstance(v, dict):
        return _truncate(repr(v), max_len)
    return _truncate(repr(v), max_len)


def _summarize_payload(payload: Dict[str, Any], max_len: int) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in payload.items():
        out[k] = _summarize_value(v, max_len)
    return out


@dataclass
class JsonlTraceSink:
    enabled: bool
    path: str
    include_payload: bool = True
    max_value_len: int = 120

    _fh: Optional[Any] = None

    def open(self) -> None:
        if not self.enabled:
            return
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def close(self) -> None:
        if self._fh:
            try:
                self._fh.close()
            finally:
                self._fh = None

    def write(self, record: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        if self._fh is None:
            self.open()
        assert self._fh is not None
        self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._fh.flush()


@dataclass
class EventScheduler:
    state: Dict[str, Any] = field(default_factory=dict)
    procedures_by_event: Dict[str, List[Procedure]] = field(default_factory=dict)
    queue: Deque[RuntimeEvent] = field(default_factory=deque)

    # Console trace (optional)
    trace: bool = False
    trace_payload: bool = False
    trace_max_value_len: int = 90

    # JSONL trace (optional)
    trace_sink: Optional[JsonlTraceSink] = None

    _event_counter: int = 0
    _cycle_id: int = 0  # increments on PoseTick

    def close(self) -> None:
        if self.trace_sink:
            self.trace_sink.close()

    def _log(self, msg: str) -> None:
        logger = self.state.get("logger")
        if logger is not None:
            logger.info(msg)
        else:
            print(msg)

    def _trace(self, msg: str) -> None:
        if self.trace:
            self._log(msg)

    def _trace_json(self, kind: str, name: str, payload: Dict[str, Any], procedure: Optional[str] = None, t: Optional[float] = None) -> None:
        if not self.trace_sink or not self.trace_sink.enabled:
            return

        if t is None:
            t = time.time()

        # Best-effort human_id extraction
        human_id = payload.get("human_id")

        rec: Dict[str, Any] = {
            "ts": t,
            "seq": self._event_counter,
            "cycle_id": self._cycle_id,
            "kind": kind,           # emit / dispatch / run / register
            "name": name,           # event name (or for register: event bound to)
            "procedure": procedure, # optional
            "human_id": human_id,
        }

        if self.trace_sink.include_payload:
            rec["payload"] = _summarize_payload(payload, self.trace_sink.max_value_len)

        self.trace_sink.write(rec)

    def emit(self, name: str, payload: Optional[Dict[str, Any]] = None, t: Optional[float] = None) -> None:
        if payload is None:
            payload = {}
        if t is None:
            t = time.time()

        self._event_counter += 1

        # increment cycle on PoseTick so downstream events share cycle_id
        if name == "PoseTick":
            self._cycle_id += 1

        ev = RuntimeEvent(name=name, payload=payload, t=t)
        self.queue.append(ev)

        # JSONL trace
        self._trace_json(kind="emit", name=name, payload=payload, procedure=None, t=t)

        # Console trace
        if self.trace:
            if self.trace_payload:
                p = _summarize_payload(payload, self.trace_max_value_len)
                self._trace(f"[TRACE] emit   #{self._event_counter:05d}  {name}  payload={p}")
            else:
                self._trace(f"[TRACE] emit   #{self._event_counter:05d}  {name}")

    def register(self, event_name: str, procedure: Procedure) -> None:
        self.procedures_by_event.setdefault(event_name, []).append(procedure)
        self._trace_json(kind="register", name=event_name, payload={}, procedure=procedure.name, t=time.time())
        if self.trace:
            self._trace(f"[TRACE] register      on={event_name}  proc={procedure.name}")

    def run_until_idle(self, max_events: int = 1000) -> int:
        processed = 0
        while self.queue and processed < max_events:
            event = self.queue.popleft()
            processed += 1
            self._dispatch(event)
        return processed

    def _dispatch(self, event: RuntimeEvent) -> None:
        # JSONL
        self._trace_json(kind="dispatch", name=event.name, payload=event.payload, procedure=None, t=event.t)

        # Console
        if self.trace:
            if self.trace_payload:
                p = _summarize_payload(event.payload, self.trace_max_value_len)
                self._trace(f"[TRACE] dispatch        {event.name}  payload={p}")
            else:
                self._trace(f"[TRACE] dispatch        {event.name}")

        procs = self.procedures_by_event.get(event.name, [])
        for proc in procs:
            if proc.can_run(self, event):
                # JSONL
                self._trace_json(kind="run", name=event.name, payload=event.payload, procedure=proc.name, t=event.t)

                # Console
                self._trace(f"[TRACE] run            proc={proc.name}  on={event.name}")

                proc.run(self, event)


# Helper constructors for readable registration
def make_condition(name: str, fn: Callable[[EventScheduler, RuntimeEvent], bool]) -> Condition:
    return Condition(name=name, check=fn)


def make_procedure(
    name: str,
    fn: Callable[[EventScheduler, RuntimeEvent], None],
    conditions: Optional[List[Condition]] = None,
) -> Procedure:
    cond_map: Dict[str, Condition] = {}
    if conditions:
        cond_map = {c.name: c for c in conditions}
    return Procedure(name=name, run=fn, conditions=cond_map)
