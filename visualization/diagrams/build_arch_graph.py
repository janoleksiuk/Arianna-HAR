from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _q(s: str) -> str:
    """Graphviz-safe quoted id/label."""
    s = s.replace('"', '\\"')
    return f"\"{s}\""


@dataclass
class ArchGraphSpec:
    system_name: str
    # registrations: event_name -> list of procedure names
    event_to_procs: Dict[str, List[str]]
    # emits: procedure_name -> list of emitted event names
    proc_emits: Dict[str, List[str]]

    # domain info
    action_names: List[str]
    family_count: int
    task_names: List[str]
    pretask_names: List[str]


def export_architecture_graph(
    spec: ArchGraphSpec,
    output_dir: str,
    basename: str = "architecture",
    render_svg: bool = True,
    overwrite: bool = True,
) -> Dict[str, str]:
    """
    Writes:
      - <output_dir>/<basename>.dot
      - <output_dir>/<basename>.svg (if render_svg and 'dot' found)

    Returns dict with written paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    dot_path = os.path.join(output_dir, f"{basename}.dot")
    svg_path = os.path.join(output_dir, f"{basename}.svg")

    if (not overwrite) and os.path.exists(dot_path):
        raise FileExistsError(dot_path)

    dot = _build_dot(spec)

    with open(dot_path, "w", encoding="utf-8") as f:
        f.write(dot)

    out = {"dot": dot_path}

    if render_svg:
        dot_exe = shutil.which("dot")
        if dot_exe:
            try:
                subprocess.run(
                    [dot_exe, "-Tsvg", dot_path, "-o", svg_path],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                out["svg"] = svg_path
            except subprocess.CalledProcessError as e:
                # Keep DOT even if SVG fails
                out["svg_error"] = (e.stderr or str(e))
        else:
            out["svg_error"] = "Graphviz 'dot' not found on PATH. Install Graphviz or disable ARCH_DIAGRAM_RENDER_SVG."

    return out


def _build_dot(spec: ArchGraphSpec) -> str:
    # ---- node style helpers ----
    def node(name: str, shape: str, style: str = "rounded", fill: Optional[str] = None) -> str:
        attrs = [f"shape={shape}", f"style={_q(style)}"]
        if fill is not None:
            attrs.append("style=" + _q(style + ",filled"))
            attrs.append(f"fillcolor={_q(fill)}")
        return f"{_q(name)} [{', '.join(attrs)}];"

    def edge(src: str, dst: str, label: Optional[str] = None, style: Optional[str] = None) -> str:
        attrs = []
        if label:
            attrs.append(f"label={_q(label)}")
        if style:
            attrs.append(f"style={_q(style)}")
        if attrs:
            return f"{_q(src)} -> {_q(dst)} [{', '.join(attrs)}];"
        return f"{_q(src)} -> {_q(dst)};"

    # ---- derive all nodes ----
    all_events = set(spec.event_to_procs.keys())
    for outs in spec.proc_emits.values():
        all_events.update(outs)

    all_procs = set()
    for procs in spec.event_to_procs.values():
        all_procs.update(procs)

    # ---- DOT ----
    lines: List[str] = []
    lines.append("digraph Architecture {")
    lines.append("  rankdir=LR;")
    lines.append("  compound=true;")
    lines.append("  fontname=\"Arial\";")
    lines.append("  labelloc=\"t\";")
    lines.append(f"  label={_q(f'{spec.system_name} — Event/Procedure Architecture')};")
    lines.append("  node [fontname=\"Arial\"];")
    lines.append("  edge [fontname=\"Arial\"];")
    lines.append("")

    # Global nodes
    lines.append(node("Scheduler", "box", fill="#F2F2F2"))
    lines.append(node("UpperOntology (OU)", "folder", fill="#FFF7E6"))
    lines.append(node("MemoryStore (per-human)", "folder", fill="#FFF7E6"))
    lines.append(node("PoseDetectorSim", "component", fill="#E8F5E9"))
    lines.append(node("SpotRobotSim", "component", fill="#E3F2FD"))
    lines.append("")

    # Events cluster
    lines.append("  subgraph cluster_events {")
    lines.append("    label=\"Events\";")
    lines.append("    style=\"rounded\";")
    lines.append("    color=\"#BBBBBB\";")
    for ev in sorted(all_events):
        lines.append("    " + node(f"Event::{ev}", "ellipse", fill="#FFFFFF"))
    lines.append("  }")
    lines.append("")

    # Procedures cluster
    lines.append("  subgraph cluster_procs {")
    lines.append("    label=\"Procedures\";")
    lines.append("    style=\"rounded\";")
    lines.append("    color=\"#BBBBBB\";")
    for p in sorted(all_procs):
        lines.append("    " + node(f"Proc::{p}", "box", fill="#FFFFFF"))
    lines.append("  }")
    lines.append("")

    # Ontologies cluster
    lines.append("  subgraph cluster_ont {")
    lines.append("    label=\"Ontologies / Knowledge\";")
    lines.append("    style=\"rounded\";")
    lines.append("    color=\"#BBBBBB\";")
    lines.append("    " + node("PerceptionOntology (OP)", "folder", fill="#FFF7E6"))
    lines.append("    " + node("HumanStateOntology (OS)", "folder", fill="#FFF7E6"))
    lines.append("    " + node("HumanActionOntology (OA)", "folder", fill="#FFF7E6"))
    lines.append("    " + node("RobotOntology (OR)", "folder", fill="#FFF7E6"))
    lines.append("  }")
    lines.append("")

    # Domain definitions cluster
    lines.append("  subgraph cluster_domain {")
    lines.append("    label=\"Domain Definitions (from config)\";")
    lines.append("    style=\"rounded\";")
    lines.append("    color=\"#BBBBBB\";")
    lines.append("    " + node(f"Actions ({len(spec.action_names)})", "note", fill="#FFFFFF"))
    lines.append("    " + node(f"Families ({spec.family_count})", "note", fill="#FFFFFF"))
    lines.append("    " + node(f"Tasks ({len(spec.task_names)})", "note", fill="#FFFFFF"))
    lines.append("    " + node(f"Pretasks ({len(spec.pretask_names)})", "note", fill="#FFFFFF"))
    lines.append("  }")
    lines.append("")

    # Core wiring (high-level)
    lines.append(edge("PoseDetectorSim", "Event::PoseTick", "emits"))
    lines.append(edge("Scheduler", "Event::PoseTick", "dispatches", style="dashed"))

    # Registration edges: Event -> Procedure (trigger)
    for ev, procs in spec.event_to_procs.items():
        for p in procs:
            lines.append(edge(f"Event::{ev}", f"Proc::{p}", "triggers"))

    # Emit edges: Procedure -> Event
    for p, outs in spec.proc_emits.items():
        for ev_out in outs:
            lines.append(edge(f"Proc::{p}", f"Event::{ev_out}", "emits", style="dashed"))

    # Procedure -> Ontology (semantic mapping; keep it simple and readable)
    # These names match your current main.py procedure names.
    # If you rename procedures later, just adjust this mapping (or we can auto-map).
    lines.append(edge("Proc::PerceptionToPoseSegment", "PerceptionOntology (OP)", "updates"))
    lines.append(edge("Proc::UpdateHumanState", "HumanStateOntology (OS)", "updates"))
    lines.append(edge("Proc::ComputeEarlyIntent", "HumanActionOntology (OA)", "reads/infers"))
    lines.append(edge("Proc::DetectAction", "HumanActionOntology (OA)", "reads/infers"))
    lines.append(edge("Proc::PrepareFamilyPretask", "RobotOntology (OR)", "prepares"))
    lines.append(edge("Proc::DispatchTask", "RobotOntology (OR)", "executes"))
    lines.append(edge("Proc::OnTaskCompleted", "UpperOntology (OU)", "mode/episode"))
    lines.append(edge("Proc::ResetTickFlags", "UpperOntology (OU)", "coordination", style="dotted"))

    # Robot execution links
    lines.append(edge("Proc::PrepareFamilyPretask", "SpotRobotSim", "async pretask"))
    lines.append(edge("Proc::DispatchTask", "SpotRobotSim", "task"))

    # Memory
    lines.append(edge("Proc::PerceptionToPoseSegment", "MemoryStore (per-human)", "writes"))
    lines.append(edge("Proc::DetectAction", "MemoryStore (per-human)", "writes"))
    lines.append(edge("Proc::DispatchTask", "MemoryStore (per-human)", "writes"))
    lines.append(edge("Proc::OnTaskCompleted", "MemoryStore (per-human)", "clears"))

    # Domain defs connections
    lines.append(edge("HumanActionOntology (OA)", f"Actions ({len(spec.action_names)})", "loads"))
    lines.append(edge("HumanActionOntology (OA)", f"Families ({spec.family_count})", "builds"))
    lines.append(edge("RobotOntology (OR)", f"Tasks ({len(spec.task_names)})", "loads"))
    lines.append(edge("RobotOntology (OR)", f"Pretasks ({len(spec.pretask_names)})", "loads"))

    lines.append("}")
    return "\n".join(lines)

