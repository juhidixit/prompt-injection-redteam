"""Command line entry point: `python -m pirt <command>`."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="pirt", description="Prompt-injection red-team lab for tool-using agents")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="run benign + attacked episodes for a model x defense grid")
    r.add_argument("--model", required=True,
                   help="path to a .gguf file, 'scripted' (fake agent), or 'openai:<model>' "
                        "for an OpenAI-compatible API")
    r.add_argument("--defenses", default="none", help="comma-separated, e.g. none,sandwich,tool_guard,layered")
    r.add_argument("--out", required=True, help="JSONL output (resumable)")
    r.add_argument("--tasks", default=None, help="comma-separated task ids (default: all)")
    r.add_argument("--threads", type=int, default=None)
    r.add_argument("--full", action="store_true", help="every goal for every (task, template) pair")

    a = sub.add_parser("adaptive", help="adaptive LLM attacker that rewrites failed injections")
    a.add_argument("--target", required=True)
    a.add_argument("--attacker", default=None, help="attacker model (default: same as target)")
    a.add_argument("--defenses", default="none")
    a.add_argument("--rounds", type=int, default=5)
    a.add_argument("--out", required=True)
    a.add_argument("--threads", type=int, default=None)

    d = sub.add_parser("detector", help="train the injection detector and evaluate it per attack family")
    d.add_argument("--out", default="results/detector.json")
    d.add_argument("--self-check-model", default=None, help="also evaluate an LLM self-check detector")

    p = sub.add_parser("report", help="aggregate results/raw/*.jsonl into results/RESULTS.md and charts")
    p.add_argument("--raw", default="results/raw")
    p.add_argument("--out", default="results")

    args = ap.parse_args(argv)
    if args.cmd == "run":
        from .attacks import attack_suite
        from .runner import run_grid
        from .tasks import TASKS
        llm = make_llm(args.model, args.threads)
        task_ids = args.tasks.split(",") if args.tasks else [t.id for t in TASKS]
        run_grid(llm, args.defenses.split(","), args.out, task_ids, attack_suite(task_ids, full=args.full))
    elif args.cmd == "adaptive":
        from .adaptive import run_adaptive
        target = make_llm(args.target, args.threads)
        attacker = make_llm(args.attacker, args.threads) if args.attacker and args.attacker != args.target else target
        run_adaptive(target, attacker, args.defenses.split(","), args.out, rounds=args.rounds)
    elif args.cmd == "detector":
        from .detector_eval import evaluate
        evaluate(args.out, make_llm(args.self_check_model) if args.self_check_model else None)
    elif args.cmd == "report":
        from .report import build_report
        build_report(args.raw, args.out)
    else:  # pragma: no cover
        ap.print_help()
        sys.exit(2)


def make_llm(spec: str, threads: int | None = None):
    from .llm import LlamaCppLLM, OpenAICompatLLM, ScriptedLLM
    if spec == "scripted":
        return ScriptedLLM()
    if spec.startswith("openai:"):
        return OpenAICompatLLM(spec.split(":", 1)[1])
    return LlamaCppLLM(spec, n_threads=threads)


if __name__ == "__main__":
    main()
