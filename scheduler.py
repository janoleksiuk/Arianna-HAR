"""
A small event-based scheduler (Arianna+-style) with optional TRACE.

- Register procedures to event names.
- Each procedure can have conditions.
- Events are queued; scheduler processes them FIFO.
- Procedures can emit new events.

TRACE mode prints:
  - emitted events
  - dispatched events
  - procedures executed
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

from ontologies.upper_ontology import RuntimeEvent, Procedure, Condition


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"


def _summarize_value(v: Any, max_len: int) -> str:
    # common objects from this project
    if hasattr(v, "label"):  # PoseStatement-like
        return f"{v.__class__.__name__}(label={getattr(v, 'label', None)})"
    if hasattr(v, "name") and hasattr(v, "matched_sequence"):  # ActionInstance-like
        return f"{v.__class__.__name__}(name={getattr(v, 'name', None)})"
    if isinstance(v, (int, float, bool, type(None))):
        return str(v)
    if isinstance(v, str):
        return _truncate(v, max_len)
    # fallback
    return _truncate(repr(v), max_len)


def _summarize_payload(payload: Dict[str, Any], max_len: int) -> str:
    if not payload:
        return "{}"
    parts = []
    for k, v in payload.items():
        parts.append(f"{k}={_summarize_value(v, max_len)}")
    return "{ " + ", ".join(parts) + " }"


@dataclass
class EventScheduler:
    """
    Minimal event scheduler.

    state: a shared blackboard dictionary (global for your system).
    procedures_by_event: mapping from event_name -> list of Procedure
    """
    state: Dict[str, Any] = field(default_factory=dict)
    procedures_by_event: Dict[str, List[Procedure]] = field(default_factory=dict)
    queue: Deque[RuntimeEvent] = field(default_factory=deque)

    # tracing controls
    trace: bool = False
    trace_payload: bool = False
    trace_max_value_len: int = 90

    _event_counter: int = 0

    def _log(self, msg: str) -> None:
        logger = self.state.get("logger")
        if logger is not None:
            logger.info(msg)
        else:
            print(msg)

    def _trace(self, msg: str) -> None:
        if self.trace:
            self._log(msg)

    def emit(self, name: str, payload: Optional[Dict[str, Any]] = None, t: Optional[float] = None) -> None:
        if payload is None:
            payload = {}
        if t is None:
            t = time.time()

        self._event_counter += 1
        ev = RuntimeEvent(name=name, payload=payload, t=t)
        self.queue.append(ev)

        if self.trace:
            if self.trace_payload:
                p = _summarize_payload(payload, self.trace_max_value_len)
                self._trace(f"[TRACE] emit   #{self._event_counter:05d}  {name}  payload={p}")
            else:
                self._trace(f"[TRACE] emit   #{self._event_counter:05d}  {name}")

    def register(self, event_name: str, procedure: Procedure) -> None:
        self.procedures_by_event.setdefault(event_name, []).append(procedure)
        if self.trace:
            self._trace(f"[TRACE] register      on={event_name}  proc={procedure.name}")

    def run_until_idle(self, max_events: int = 1000) -> int:
        """
        Process queued events until empty or until max_events processed.
        Returns the number of processed events.
        """
        processed = 0
        while self.queue and processed < max_events:
            event = self.queue.popleft()
            processed += 1
            self._dispatch(event)
        return processed

    def _dispatch(self, event: RuntimeEvent) -> None:
        if self.trace:
            if self.trace_payload:
                p = _summarize_payload(event.payload, self.trace_max_value_len)
                self._trace(f"[TRACE] dispatch        {event.name}  payload={p}")
            else:
                self._trace(f"[TRACE] dispatch        {event.name}")

        procs = self.procedures_by_event.get(event.name, [])
        for proc in procs:
            if proc.can_run(self, event):
                self._trace(f"[TRACE] run            proc={proc.name}  on={event.name}")
                proc.run(self, event)
            else:
                # Optional: uncomment if you want to see why things don't fire
                # self._trace(f"[TRACE] skip           proc={proc.name}  on={event.name}  (condition false)")
                pass


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
