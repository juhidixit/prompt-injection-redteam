PY ?= python
MODELS_DIR ?= models
QWEN3B := $(MODELS_DIR)/qwen2.5-3B-Q4_K_M.gguf
LLAMA3B := $(MODELS_DIR)/llama3.2-3B-Q4_K_M.gguf
QWEN7B := $(MODELS_DIR)/qwen2.5-7B-Q4_K_M.gguf
ALL_DEFENSES := none,delimit,datamark,sandwich,classifier,self_check,tool_guard,layered

.PHONY: install data models test lint smoke bench detector adaptive report

install:            ## core + dev deps (add .[llm] to run local models)
	$(PY) -m pip install -e ".[dev]"

data:               ## public datasets used to train the injection detector
	$(PY) scripts/fetch_data.py

models:             ## GGUF weights (Docker Hub ai/ namespace)
	MODELS_DIR=$(MODELS_DIR) scripts/pull_models.sh ai/qwen2.5:3B-Q4_K_M ai/llama3.2:3B-Q4_K_M ai/qwen2.5:7B-Q4_K_M

test:
	$(PY) -m pytest -q

lint:
	ruff check .

smoke:              ## full pipeline with the scripted fake agent (no model needed, ~10 s)
	$(PY) -m pirt run --model scripted --defenses $(ALL_DEFENSES) --out /tmp/pirt_smoke.jsonl

bench:              ## the measured grid in results/ (hours on CPU; resumable)
	$(PY) -m pirt run --model $(QWEN3B) --defenses $(ALL_DEFENSES) --out results/raw/qwen2.5-3B-Q4_K_M.jsonl
	$(PY) -m pirt run --model $(LLAMA3B) --defenses $(ALL_DEFENSES) --out results/raw/llama3.2-3B-Q4_K_M.jsonl
	$(PY) -m pirt run --model $(QWEN7B) --defenses none,tool_guard,layered --out results/raw/qwen2.5-7B-Q4_K_M.jsonl

detector:
	$(PY) -m pirt detector --out results/detector.json --self-check-model $(QWEN3B)

adaptive:
	$(PY) -m pirt adaptive --target $(QWEN3B) --defenses sandwich,classifier --rounds 5 --out results/raw/adaptive_qwen3b.jsonl

report:
	$(PY) -m pirt report
