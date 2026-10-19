"""Tests for the eval scorer (dreamcare_mcp.evals.score) and the eval set (evals/cases.json).

The scorer is pure: given a case and the tool calls an agent made, it says pass or
fail and why. No model, no server, so these tests are fast and exact.
"""

import datetime as dt
import json
from pathlib import Path

import pytest
from mcp import Client

from dreamcare_mcp.evals import Case, ExpectedCall, ToolCall, load_cases, score
from dreamcare_mcp.seed import seed_demo
from dreamcare_mcp.server import create_server


def make_case(**overrides) -> Case:
    fields = dict(
        id="confirm-taken",
        utterance="Sí, ya me tomé la metformina",
        now_utc="2026-10-19T14:05:00+00:00",
        required_calls=[ExpectedCall("confirm_intake", {"medication_id": 1, "status": "taken"})],
        forbidden_tools=[],
    )
    fields.update(overrides)
    return Case(**fields)


def test_exact_expected_call_passes():
    result = score(make_case(), [ToolCall("confirm_intake", {"medication_id": 1, "status": "taken"})])

    assert result.passed
    assert result.reasons == []


def test_missing_required_call_fails_with_reason():
    result = score(make_case(), [])

    assert not result.passed
    assert "confirm_intake" in result.reasons[0]


def test_wrong_argument_value_fails():
    result = score(make_case(), [ToolCall("confirm_intake", {"medication_id": 1, "status": "missed"})])

    assert not result.passed


def test_extra_arguments_are_allowed():
    case = make_case(required_calls=[ExpectedCall("get_due_medications", {})])

    result = score(case, [ToolCall("get_due_medications", {"window_minutes": 30})])

    assert result.passed


def test_extra_read_only_calls_before_the_required_one_are_allowed():
    calls = [
        ToolCall("list_medications", {}),
        ToolCall("confirm_intake", {"medication_id": 1, "status": "taken"}),
    ]

    assert score(make_case(), calls).passed


def test_required_calls_must_happen_in_order():
    case = make_case(required_calls=[
        ExpectedCall("get_due_medications", {}),
        ExpectedCall("confirm_intake", {"medication_id": 1, "status": "taken"}),
    ])
    calls = [
        ToolCall("confirm_intake", {"medication_id": 1, "status": "taken"}),
        ToolCall("get_due_medications", {}),
    ]

    assert not score(case, calls).passed


@pytest.mark.parametrize(
    "calls",
    [
        [ToolCall("confirm_intake", {"medication_id": 1, "status": "taken"})],
        [ToolCall("list_medications", {}), ToolCall("confirm_intake", {"medication_id": 2, "status": "missed"})],
    ],
    ids=["only-forbidden", "forbidden-after-required"],
)
def test_calling_a_forbidden_tool_fails(calls):
    case = make_case(required_calls=[ExpectedCall("list_medications", {})], forbidden_tools=["confirm_intake"])

    result = score(case, calls)

    assert not result.passed
    assert any("confirm_intake" in r and "forbidden" in r for r in result.reasons)


def test_case_with_no_required_calls_passes_when_agent_calls_nothing():
    case = make_case(required_calls=[], forbidden_tools=["confirm_intake"])

    assert score(case, []).passed


# --- the eval set itself -------------------------------------------------------
#
# These checks keep cases.json honest: every tool it names exists, and replaying
# each case's expected calls against the real server (demo data, the case's clock)
# succeeds and returns what the case says it should.

CASES_PATH = Path(__file__).parents[1] / "evals" / "cases.json"
CASES = load_cases(CASES_PATH)


def test_case_ids_are_unique():
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids))


@pytest.mark.anyio
@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
async def test_expected_calls_succeed_against_the_real_server(repo, case):
    user_id = seed_demo(repo)
    now = dt.datetime.fromisoformat(case.now_utc)
    server = create_server(repo, user_id, clock=lambda: now)

    async with Client(server) as client:
        tool_names = {t.name for t in (await client.list_tools()).tools}
        assert {c.tool for c in case.required_calls} <= tool_names
        assert set(case.forbidden_tools) <= tool_names

        outputs = []
        for expected in case.required_calls:
            result = await client.call_tool(expected.tool, expected.arguments)
            assert not result.is_error, result.content[0].text
            outputs.append(result.structured_content)

    text = json.dumps(outputs, ensure_ascii=False)
    for word in case.expected_mentions:
        assert word in text
    for word in case.forbidden_mentions:
        assert word not in text
