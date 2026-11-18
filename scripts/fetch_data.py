"""Download external data used to train the injection detector into data/external/.

Not committed to the repo (each source keeps its own license):
  * Tensor Trust hijacking-robustness attacks (Toyer et al. 2023) - injection positives
  * BIPIA email contexts (Microsoft, MIT)                         - benign negatives
  * NLTK webtext + Reuters-21578 corpora                          - benign negatives
"""

import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "external"
RAW = "https://raw.githubusercontent.com"
SOURCES = {
    "tensor_trust_hijacking.jsonl":
        f"{RAW}/HumanCompatibleAI/tensor-trust-data/main/benchmarks/hijacking-robustness/v1/hijacking_robustness_dataset.jsonl",
    "bipia_email_train.jsonl": f"{RAW}/microsoft/BIPIA/main/benchmark/email/train.jsonl",
    "bipia_email_test.jsonl": f"{RAW}/microsoft/BIPIA/main/benchmark/email/test.jsonl",
    "webtext.zip": f"{RAW}/nltk/nltk_data/gh-pages/packages/corpora/webtext.zip",
    "reuters.zip": f"{RAW}/nltk/nltk_data/gh-pages/packages/corpora/reuters.zip",
}


def get(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        if (OUT / name).exists() or (name.endswith(".zip") and (OUT / name.replace(".zip", ".jsonl")).exists()):
            continue
        print("fetching", url, file=sys.stderr)
        data = get(url)
        if not name.endswith(".zip"):
            (OUT / name).write_bytes(data)
            continue
        # keep paragraphs of plain text only
        paras = []
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for f in z.namelist():
                if f.endswith("/") or "README" in f or "cats.txt" in f or "stopwords" in f:
                    continue
                txt = z.read(f).decode("latin-1")
                for p in re.split(r"\n\s*\n|\n", txt):
                    p = " ".join(p.split())
                    if 5 <= len(p.split()) <= 120:
                        paras.append(p)
        with open(OUT / name.replace(".zip", ".jsonl"), "w") as fh:
            for p in paras:
                fh.write(json.dumps({"text": p}) + "\n")
    print("ok", file=sys.stderr)


if __name__ == "__main__":
    main()
