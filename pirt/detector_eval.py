"""Evaluate injection detectors per attack family on this repo's (unseen) attack corpus."""

from __future__ import annotations

import json
from pathlib import Path

from .attacks import GOALS, TEMPLATE_IDS, render
from .defenses import SELF_CHECK_PROMPT, split_segments
from .detector import MIN_WORDS, train
from .tasks import base_workspace


def benign_workspace_segments() -> list[str]:
    ws = base_workspace()
    texts = [e.body for e in ws.emails] + list(ws.files.values()) + list(ws.web.values())
    return [s for t in texts for s in split_segments(t) if len(s.split()) >= MIN_WORDS]


def evaluate(out: str | Path, self_check_llm=None) -> dict:
    det, stats = train()
    attacks = {t: [render(t, g) for g in GOALS] for t in TEMPLATE_IDS}
    benign = benign_workspace_segments()
    res = {"classifier": {"training": stats, "per_family": {}, "benign_workspace_fpr": None}}
    for t, texts in attacks.items():
        res["classifier"]["per_family"][t] = sum(det.is_injection(x) for x in texts) / len(texts)
    flagged = [s for s in benign if det.is_injection(s)]
    res["classifier"]["benign_workspace_fpr"] = len(flagged) / len(benign)
    res["classifier"]["benign_flagged"] = flagged
    res["n_benign_segments"] = len(benign)
    res["n_attacks_per_family"] = len(GOALS)
    if self_check_llm is not None:
        def yes(text: str) -> bool:
            v = self_check_llm.chat([{"role": "system", "content": SELF_CHECK_PROMPT},
                                     {"role": "user", "content": f"Text:\n\"\"\"\n{text}\n\"\"\""}], max_tokens=4)
            return v.strip().upper().startswith("YES")
        sc = {"per_family": {t: sum(yes(x) for x in texts) / len(texts) for t, texts in attacks.items()}}
        fl = [s for s in benign if yes(s)]
        sc["benign_workspace_fpr"] = len(fl) / len(benign)
        sc["benign_flagged"] = fl
        sc["model"] = self_check_llm.name
        res["self_check"] = sc
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res, indent=1))
    return res
