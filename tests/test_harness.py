import json

import pytest

from pirt.agent import parse_action, run_agent
from pirt.attacks import GOALS, TEMPLATE_IDS, AttackCase, attack_suite, render
from pirt.defenses import Datamark, ToolGuard, build, split_segments
from pirt.env import call_tool
from pirt.llm import ScriptedLLM
from pirt.metrics import wilson
from pirt.runner import run_episode
from pirt.tasks import TASKS, base_workspace


def test_parse_action_variants():
    assert parse_action('{"tool": "read_email", "args": {"id": 1}}') == {"tool": "read_email", "args": {"id": 1}}
    assert parse_action('```json\n{"name": "read_file", "arguments": {"path": "a"}}\n```')["tool"] == "read_file"
    assert parse_action('Sure! {"answer": "done"} hope that helps') == {"answer": "done"}
    assert parse_action("no json here") is None
    assert parse_action('{"answer": "has { brace"}') == {"answer": "has { brace"}


def test_suite_is_balanced():
    cases = attack_suite([t.id for t in TASKS])
    assert len(cases) == len(TASKS) * len(TEMPLATE_IDS)
    for g in GOALS:
        assert sum(c.goal_id == g.id for c in cases) == len(cases) // len(GOALS)
    assert len(attack_suite([t.id for t in TASKS], full=True)) == len(TASKS) * len(TEMPLATE_IDS) * len(GOALS)


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_oracle_solves_every_task(task):
    ws = base_workspace()
    for name, args in task.oracle:
        call_tool(ws, name, args)
    assert task.check(ws, task.oracle_answer)


def test_tasks_fail_without_work():
    for task in TASKS:
        assert not task.check(base_workspace(), "I don't know.")


@pytest.mark.parametrize("goal", GOALS, ids=lambda g: g.id)
def test_goal_success_predicates(goal):
    ws = base_workspace()
    assert not goal.succeeded(ws, "fine")
    call = goal.tool_call
    if "tool" in call:
        call_tool(ws, call["tool"], call["args"])
        assert goal.succeeded(ws, "")
    else:
        assert goal.succeeded(ws, call["answer"])


def test_scripted_agent_end_to_end():
    llm = ScriptedLLM()
    benign = run_episode(llm, "none", "email_reply")
    assert benign["utility"] and benign["attack_success"] is None
    rec = run_episode(llm, "none", "web_pricing", AttackCase("web_pricing", "naive", "payment"))
    assert rec["attack_success"] and rec["exposed"]


def test_tool_guard_blocks_ungrounded_actions_but_allows_user_requested_ones():
    llm = ScriptedLLM()
    for goal in ("exfiltrate", "payment", "delete"):
        rec = run_episode(llm, "tool_guard", "file_runbook", AttackCase("file_runbook", "naive", goal))
        assert not rec["attack_success"] and rec["blocked_calls"] == 1
    assert run_episode(llm, "tool_guard", "file_pay_invoice")["utility"]
    assert run_episode(llm, "tool_guard", "email_reply")["utility"]
    g = ToolGuard()
    ctx = {"task": "delete the file tmp/x.txt please", "ws": base_workspace()}
    assert g.check_tool_call("delete_file", {"path": "tmp/x.txt"}, ctx) is None
    assert g.check_tool_call("read_file", {"path": "anything"}, ctx) is None


def test_datamark_and_segments():
    assert Datamark().process_tool_output("t", "a b  c", {}) == "aˆbˆc"
    segs = split_segments("line one\nline two\n\n<INFORMATION>\nx\ny\n</INFORMATION>")
    assert segs[:2] == ["line one", "line two"] and segs[2].startswith("<INFORMATION>")


def test_self_check_defense_with_scripted_llm():
    rec = run_episode(ScriptedLLM(), "self_check", "web_news", AttackCase("web_news", "fake_system", "phishing"))
    assert not rec["attack_success"] and not rec["exposed"] and rec["llm_calls"] > rec["n_steps"]


def test_every_defense_builds_and_runs():
    for name in ["none", "delimit", "datamark", "sandwich", "self_check", "tool_guard"]:
        ep = run_agent(ScriptedLLM(), base_workspace(), TASKS[0].prompt, build(name))
        assert ep.answer


def test_templates_render_goal():
    for g in GOALS:
        for t in TEMPLATE_IDS:
            text = render(t, g)
            assert isinstance(text, str) and len(text) > 20
    assert json.loads(render("tool_spoof", GOALS[1]).split("\n", 1)[1])["tool"] == "pay_invoice"


def test_wilson():
    p, lo, hi = wilson(5, 10)
    assert p == 0.5 and 0.2 < lo < 0.5 < hi < 0.8
    assert wilson(0, 20)[1] == 0.0
