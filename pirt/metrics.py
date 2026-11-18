"""Aggregation with Wilson score intervals."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def load(paths) -> list[dict]:
    rows = []
    for p in paths if isinstance(paths, (list, tuple)) else [paths]:
        rows += [json.loads(line) for line in Path(p).read_text().splitlines() if line.strip()]
    return rows


def rate(rows: list[dict], field: str) -> dict:
    k = sum(1 for r in rows if r[field])
    n = len(rows)
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "p": p, "lo": lo, "hi": hi}


def group(rows: list[dict], *keys: str) -> dict[tuple, list[dict]]:
    g: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in keys)].append(r)
    return dict(g)


def fmt(stat: dict, ci: bool = True) -> str:
    if stat["n"] == 0:
        return "-"
    s = f"{100 * stat['p']:.1f}%"
    return f"{s} [{100 * stat['lo']:.0f}-{100 * stat['hi']:.0f}]" if ci else s
