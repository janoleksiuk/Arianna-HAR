"""Optional visualization helpers (text-only for now)."""

from __future__ import annotations

from typing import Dict, List


def format_pose_buffer(pose_labels: List[str]) -> str:
    return " -> ".join(pose_labels)


def format_candidates(candidates: Dict[str, List[int]]) -> str:
    parts = []
    for a, lens in sorted(candidates.items()):
        parts.append(f"{a}(prefix_len={max(lens)})")
    return ", ".join(parts) if parts else "<none>"

