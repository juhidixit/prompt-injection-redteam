"""A lightweight prompt-injection detector (TF-IDF word+char n-grams, logistic regression).

Trained only on *public* attack text (BIPIA text-attack instructions; Tensor Trust
hijacking attacks) and benign text (Reuters, NLTK webtext, BIPIA emails, pirt.benign).
It never sees this repo's attack templates, goals or workspace, so its numbers on the
agent benchmark measure generalisation to unseen attack styles.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from .benign import benign_segments, injection_segments

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "bipia_text_attacks.json"
EXTERNAL = ROOT / "data" / "external"
MIN_WORDS = 5  # shorter segments (greetings, headers, sign-offs) are not scored


def _flatten(d: dict[str, list[str]]) -> list[str]:
    return [s for v in d.values() for s in v]


@dataclass
class Detector:
    pipeline: object
    threshold: float

    def score(self, texts: list[str]) -> np.ndarray:
        return self.pipeline.predict_proba(texts)[:, 1]

    def is_injection(self, text: str) -> bool:
        if len(text.split()) < MIN_WORDS:
            return False
        return bool(self.score([text])[0] >= self.threshold)


def _jsonl(name: str) -> list[dict]:
    path = EXTERNAL / name
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: run `python scripts/fetch_data.py` first")
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_corpus(seed: int = 0) -> dict[str, tuple[list[str], list[str]]]:
    """Return {"train": (pos, neg), "val": (pos, neg)} from external data + synthetic benign text."""
    rng = random.Random(seed)
    bipia = json.loads(DATA.read_text())
    tt = [r["attack"][:800] for r in _jsonl("tensor_trust_hijacking.jsonl") if r["attack"].strip()]
    rng.shuffle(tt)
    cut = int(0.8 * len(tt))
    pos_tr = injection_segments(_flatten(bipia["train"]), seed=seed) + tt[:cut]
    pos_va = injection_segments(_flatten(bipia["test"]), seed=seed + 1) + tt[cut:]

    def benign(name: str, k: int) -> list[str]:
        rows = [r["text"] for r in _jsonl(name)]
        return rng.sample(rows, min(k, len(rows)))

    emails = [seg for f in ("bipia_email_train.jsonl", "bipia_email_test.jsonl") for r in _jsonl(f)
              for seg in re.split(r"(?<=[.!?|])\s+", r["context"].replace("|CONTENT:", ".")) if len(seg.split()) >= 5]
    rng.shuffle(emails)
    neg = benign("reuters.jsonl", 3000) + benign("webtext.jsonl", 3000) + emails + benign_segments(1500, seed=seed)
    rng.shuffle(neg)
    cut = int(0.8 * len(neg))
    return {"train": (pos_tr, neg[:cut]), "val": (pos_va, neg[cut:])}


def train(target_fpr: float = 0.01, seed: int = 0) -> tuple[Detector, dict]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline, make_union

    data = load_corpus(seed)
    pos_tr, neg_tr = data["train"]
    pos_va, neg_va = data["val"]
    X = pos_tr + neg_tr
    y = np.array([1] * len(pos_tr) + [0] * len(neg_tr))
    pipe = make_pipeline(
        make_union(TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=2),
                   TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=3)),
        LogisticRegression(C=4.0, max_iter=3000, class_weight="balanced"),
    )
    pipe.fit(X, y)
    neg_scores = pipe.predict_proba(neg_va)[:, 1]
    thr = float(np.quantile(neg_scores, 1 - target_fpr))
    pos_scores = pipe.predict_proba(pos_va)[:, 1]
    stats = {"n_train_pos": len(pos_tr), "n_train_neg": len(neg_tr), "threshold": round(thr, 4),
             "val_fpr": round(float((neg_scores >= thr).mean()), 4),
             "val_tpr": round(float((pos_scores >= thr).mean()), 4), "n_val_pos": len(pos_va), "n_val_neg": len(neg_va)}
    return Detector(pipe, thr), stats


@lru_cache(maxsize=1)
def load_default() -> Detector:
    return train()[0]
