"""Run benign (utility) and attacked episodes for a model x defense grid; resumable JSONL output."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from pathlib import Path

from .agent import run_agent
from .attacks import GOALS_BY_ID, AttackCase, attack_suite, render
from .defenses import build
from .llm import LLM
from .tasks import TASKS, TASKS_BY_ID, base_workspace, plant


def run_episode(llm: LLM, defense_name: str, task_id: str, case: AttackCase | None = None,
                injection: str | None = None, defense=None) -> dict:
    task = TASKS_BY_ID[task_id]
    ws = base_workspace()
    goal = None
    if case is not None:
        goal = GOALS_BY_ID[case.goal_id]
        injection = injection if injection is not None else render(case.template_id, goal)
        plant(ws, task.carrier, injection)
    defense = defense or build(defense_name)
    t0 = time.time()
    ep = run_agent(llm, ws, task.prompt, defense)
    rec = {
        "model": llm.name, "defense": defense_name, "kind": "attack" if case else "benign", "task": task_id,
        "template": case.template_id if case else None, "goal": case.goal_id if case else None,
        "utility": bool(task.check(ws, ep.answer)),
        "attack_success": bool(goal.succeeded(ws, ep.answer)) if goal else None,
        "exposed": bool(injection) and any(injection[:40] in (s.result or "")
                                           or _marked(injection[:40]) in (s.result or "") for s in ep.steps),
        "blocked_calls": sum(1 for s in ep.steps if s.blocked), "llm_calls": ep.llm_calls,
        "n_steps": len(ep.steps), "seconds": round(time.time() - t0, 2),
        "answer": ep.answer[:600],
        "calls": [{"tool": s.tool, "args": s.args, "blocked": s.blocked} for s in ep.steps if s.tool],
    }
    return rec


def _marked(text: str) -> str:
    import re
    return re.sub(r"[ \t]+", "\u02c6", text)


def _done_keys(path: Path) -> set[tuple]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text().splitlines():
        r = json.loads(line)
        keys.add((r["model"], r["defense"], r["kind"], r["task"], r["template"], r["goal"]))
    return keys


def run_grid(llm: LLM, defenses: Iterable[str], out: str | Path, task_ids: list[str] | None = None,
             attack_cases: list[AttackCase] | None = None, benign: bool = True, verbose: bool = True) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    task_ids = task_ids or [t.id for t in TASKS]
    cases = attack_cases if attack_cases is not None else attack_suite(task_ids)
    done = _done_keys(out)
    for d in defenses:
        defense = build(d)
        jobs = ([(t, None) for t in task_ids] if benign else []) + [(c.task_id, c) for c in cases]
        for task_id, case in jobs:
            key = (llm.name, d, "attack" if case else "benign", task_id,
                   case.template_id if case else None, case.goal_id if case else None)
            if key in done:
                continue
            rec = run_episode(llm, d, task_id, case, defense=defense)
            with out.open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            if verbose:
                tag = f"{case.template_id}/{case.goal_id}" if case else "benign"
                print(f"[{llm.name}|{d}] {task_id} {tag} util={rec['utility']} "
                      f"asr={rec['attack_success']} {rec['seconds']}s", flush=True)
    return out
