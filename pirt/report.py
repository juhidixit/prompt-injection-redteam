"""Turn raw JSONL results into results/RESULTS.md, results/summary.json and charts."""

from __future__ import annotations

import json
from pathlib import Path

from .attacks import GOALS, TEMPLATE_IDS
from .defenses import DEFENSES
from .metrics import fmt, group, load, rate

PRETTY = {"none": "No defense", "delimit": "Spotlighting: delimiters", "datamark": "Spotlighting: datamarking",
          "sandwich": "Sandwich reminder", "classifier": "Injection classifier (filter)",
          "self_check": "LLM self-check (filter)", "tool_guard": "Tool-call policy guard",
          "layered": "Layered: classifier + sandwich + guard"}


def summarize(rows: list[dict]) -> dict:
    out: dict = {}
    for (model,), mrows in sorted(group(rows, "model").items()):
        out[model] = {}
        for d in [d for d in DEFENSES if any(r["defense"] == d for r in mrows)]:
            rs = [r for r in mrows if r["defense"] == d]
            ben = [r for r in rs if r["kind"] == "benign"]
            atk = [r for r in rs if r["kind"] == "attack"]
            act = [r for r in atk if r["goal"] != "phishing"]
            out[model][d] = {
                "benign_utility": rate(ben, "utility"),
                "asr": rate(atk, "attack_success"),
                "asr_actions": rate(act, "attack_success"),
                "asr_phishing": rate([r for r in atk if r["goal"] == "phishing"], "attack_success"),
                "utility_under_attack": rate(atk, "utility"),
                "exposure": rate(atk, "exposed"),
                "asr_by_template": {t: rate([r for r in atk if r["template"] == t], "attack_success")
                                    for t in TEMPLATE_IDS},
                "asr_by_goal": {g.id: rate([r for r in atk if r["goal"] == g.id], "attack_success") for g in GOALS},
                "mean_llm_calls": sum(r["llm_calls"] for r in rs) / max(1, len(rs)),
                "mean_seconds": sum(r["seconds"] for r in rs) / max(1, len(rs)),
            }
    return out


def _chart_tradeoff(summary: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = list(summary)
    fig, axes = plt.subplots(1, len(models), figsize=(5.2 * len(models), 4.6), squeeze=False, sharey=True)
    for ax, m in zip(axes[0], models, strict=True):
        for d, s in summary[m].items():
            x, y = 100 * s["asr"]["p"], 100 * s["benign_utility"]["p"]
            ax.errorbar(x, y, xerr=[[x - 100 * s["asr"]["lo"]], [100 * s["asr"]["hi"] - x]], fmt="o", ms=6,
                        color="#c0392b" if d == "none" else "#2c3e50", ecolor="#bbbbbb", capsize=2)
            ax.annotate(d, (x, y), textcoords="offset points", xytext=(6, 4), fontsize=8)
        ax.set_title(m, fontsize=10)
        ax.set_xlabel("Attack success rate (%)  [lower is better]")
        ax.set_xlim(-3, 103)
        ax.grid(alpha=0.25)
    axes[0][0].set_ylabel("Benign task utility (%)  [higher is better]")
    fig.suptitle("Security vs. utility of prompt-injection defenses", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _chart_templates(summary: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    models = [m for m in summary if "none" in summary[m]]
    if not models:
        return
    fig, ax = plt.subplots(figsize=(10, 4.2))
    w = 0.8 / len(models)
    xs = np.arange(len(TEMPLATE_IDS))
    for i, m in enumerate(models):
        vals = [100 * summary[m]["none"]["asr_by_template"][t]["p"] for t in TEMPLATE_IDS]
        ax.bar(xs + i * w, vals, w, label=m)
    ax.set_xticks(xs + w * (len(models) - 1) / 2, TEMPLATE_IDS, rotation=35, ha="right", fontsize=8)
    ax.set_ylabel("Attack success rate (%)")
    ax.set_title("Undefended agents: success rate by attack family", fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_report(raw_dir: str | Path, out_dir: str | Path) -> str:
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    rows = load(sorted(raw_dir.glob("*.jsonl"))) if any(raw_dir.glob("*.jsonl")) else []
    rows = [r for r in rows if "kind" in r]
    summary = summarize(rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    md = ["# Results", "",
          "All numbers below were produced by `make report` from the raw episode logs in `results/raw/`.",
          "Models run locally with llama.cpp (Q4_K_M GGUF, temperature 0). 95% Wilson intervals in brackets.", ""]
    if summary:
        _chart_tradeoff(summary, out_dir / "tradeoff.png")
        _chart_templates(summary, out_dir / "asr_by_family.png")
        md += ["![tradeoff](tradeoff.png)", ""]
    for m, s in summary.items():
        n_b = next(iter(s.values()))["benign_utility"]["n"]
        n_a = next(iter(s.values()))["asr"]["n"]
        md += [f"## {m}", "", f"{n_b} benign tasks, {n_a} attacked episodes per defense.", "",
               "| Defense | Benign utility | Attack success (all) | ASR: tool actions | ASR: phishing reply | "
               "Utility under attack | LLM calls / episode |",
               "|---|---|---|---|---|---|---|"]
        for d, x in s.items():
            md.append(f"| {PRETTY.get(d, d)} | {fmt(x['benign_utility'])} | **{fmt(x['asr'])}** | "
                      f"{fmt(x['asr_actions'])} | {fmt(x['asr_phishing'])} | {fmt(x['utility_under_attack'])} | "
                      f"{x['mean_llm_calls']:.2f} |")
        md.append("")
        md += ["Attack success by family (rows) and defense (columns):", "",
               "| Family | " + " | ".join(s) + " |", "|---|" + "---|" * len(s)]
        for t in TEMPLATE_IDS:
            md.append(f"| {t} | " + " | ".join(fmt(s[d]["asr_by_template"][t], ci=False) for d in s) + " |")
        md.append("")
        md += ["Attack success by attacker goal:", "", "| Goal | " + " | ".join(s) + " |", "|---|" + "---|" * len(s)]
        for g in GOALS:
            cells = " | ".join(fmt(s[d]["asr_by_goal"][g.id], ci=False) for d in s)
            md.append(f"| {g.id} ({g.category}) | {cells} |")
        md.append("")
    if summary:
        md += ["![asr by family](asr_by_family.png)", ""]

    det = out_dir / "detector.json"
    if det.exists():
        dj = json.loads(det.read_text())
        c = dj["classifier"]
        md += ["## Detector evaluation", "",
               f"Classifier trained on {c['training']['n_train_pos']} public attack strings and "
               f"{c['training']['n_train_neg']} benign texts; threshold set for 1% FPR on held-out benign text "
               f"(validation TPR {100 * c['training']['val_tpr']:.1f}%, FPR {100 * c['training']['val_fpr']:.1f}%).",
               f"Below: detection rate on this repo's attack families ({dj['n_attacks_per_family']} goals each, never "
               f"seen in training) and false-positive rate on {dj['n_benign_segments']} benign workspace segments.", "",
               "| Family | Classifier" + (" | LLM self-check" if "self_check" in dj else "") + " |",
               "|---|---|" + ("---|" if "self_check" in dj else "")]
        for t in TEMPLATE_IDS:
            row = f"| {t} | {100 * c['per_family'][t]:.0f}%"
            if "self_check" in dj:
                row += f" | {100 * dj['self_check']['per_family'][t]:.0f}%"
            md.append(row + " |")
        row = f"| **false positives (benign)** | {100 * c['benign_workspace_fpr']:.1f}%"
        if "self_check" in dj:
            row += f" | {100 * dj['self_check']['benign_workspace_fpr']:.1f}%"
        md += [row + " |", ""]

    adaptive = sorted(raw_dir.glob("adaptive*.jsonl"))
    if adaptive:
        arows = load(adaptive)
        md += ["## Adaptive attacker (ASR@k)", "",
               "Round 1 is the static `important_instructions` injection; later rounds are rewritten by the attacker "
               "LLM after seeing what the agent did.", "",
               "| Target | Attacker | Defense | pairs | ASR@1 | ASR@3 | ASR@5 |", "|---|---|---|---|---|---|---|"]
        for (tg, ak, d), rs in group(arows, "target", "attacker", "defense").items():
            cells = []
            for k in (1, 3, 5):
                hit = [dict(x=bool(r["success_round"] and r["success_round"] <= k)) for r in rs]
                cells.append(fmt(rate(hit, "x")))
            md.append(f"| {tg} | {ak} | {d} | {len(rs)} | " + " | ".join(cells) + " |")
        md.append("")
    text = "\n".join(md)
    (out_dir / "RESULTS.md").write_text(text)
    return text
