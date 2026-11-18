"""LLM backends. All return plain text for a list of chat messages.

* `LlamaCppLLM`  - local GGUF model via llama-cpp-python (used for the reported results).
* `OpenAICompatLLM` - any OpenAI-compatible /v1/chat/completions server (vLLM, Ollama,
  llama.cpp server, OpenAI, ...). Standard library only.
* `ScriptedLLM` - deterministic, gullible fake agent for tests and CI.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.request
from typing import Protocol

Message = dict[str, str]


class LLM(Protocol):
    name: str

    def chat(self, messages: list[Message], max_tokens: int = 256) -> str: ...


class LlamaCppLLM:
    def __init__(self, model_path: str, n_ctx: int = 4096, n_threads: int | None = None, seed: int = 0):
        from llama_cpp import Llama  # optional dependency

        self.name = os.path.basename(model_path).removesuffix(".gguf")
        self._llm = Llama(model_path=model_path, n_ctx=n_ctx, n_threads=n_threads or os.cpu_count(),
                          seed=seed, verbose=False)

    def chat(self, messages: list[Message], max_tokens: int = 256) -> str:
        r = self._llm.create_chat_completion(messages, max_tokens=max_tokens, temperature=0.0, seed=0)
        return r["choices"][0]["message"]["content"] or ""


class OpenAICompatLLM:
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None):
        self.name = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")

    def chat(self, messages: list[Message], max_tokens: int = 256) -> str:
        body = json.dumps({"model": self.name, "messages": messages, "max_tokens": max_tokens,
                           "temperature": 0}).encode()
        req = urllib.request.Request(f"{self.base_url}/chat/completions", data=body, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.load(resp)["choices"][0]["message"]["content"] or ""


class ScriptedLLM:
    """A fake agent that solves tasks with their oracle tool calls and obeys any injected
    instruction it can recognise in the latest tool result. It exists to test the
    harness end to end without a model; it says nothing about real model behaviour."""

    name = "scripted"

    def __init__(self, obey: bool = True):
        self.obey = obey

    def chat(self, messages: list[Message], max_tokens: int = 256) -> str:
        from .tasks import TASKS

        system = messages[0]["content"]
        last = messages[-1]["content"]
        if system.startswith("You are a security filter"):
            return "YES" if self._find_goal(last) else "NO"
        user = messages[1]["content"]
        task = next((t for t in TASKS if t.prompt in user), None)
        n_calls = sum(1 for m in messages if m["role"] == "assistant")
        goal = self._find_goal(last) if n_calls and self.obey and "blocked" not in last else None
        if goal is not None and not any(json.dumps(goal.tool_call) == m["content"] for m in messages
                                         if m["role"] == "assistant"):
            return json.dumps(goal.tool_call)
        if task is None:
            return json.dumps({"answer": "I could not find that."})
        if n_calls < len(task.oracle):
            name, args = task.oracle[n_calls]
            return json.dumps({"tool": name, "args": args})
        return json.dumps({"answer": task.oracle_answer})

    @staticmethod
    def _find_goal(text: str):
        from .attacks import ATTACKER_EMAIL, ATTACKER_IBAN, GOALS_BY_ID, PHISH_URL, TARGET_FILE

        plain = text.replace("ˆ", " ")
        for blob in re.findall(r"[A-Za-z0-9+/=]{40,}", plain):
            try:
                plain += " " + base64.b64decode(blob).decode()
            except Exception:  # noqa: BLE001
                pass
        for marker, gid in [(ATTACKER_EMAIL, "exfiltrate"), (ATTACKER_IBAN, "payment"),
                            (TARGET_FILE, "delete"), (PHISH_URL, "phishing")]:
            if marker in plain:
                return GOALS_BY_ID[gid]
        return None
