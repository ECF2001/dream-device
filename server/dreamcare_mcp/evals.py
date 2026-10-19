"""Evaluation cases for an agent using the DreamCare MCP tools, and a scorer.

A case is a user request (in Spanish, as the device would hear it) plus what a
good agent must do: the tool calls it must make, in order, and the tools it must
never call. `score()` compares that with the calls an agent actually made.

The scorer is pure, so it works with any agent (a Foundry agent, Claude, a local
model): an adapter only has to run the agent and collect its tool calls.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExpectedCall:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)   # must be included in the actual arguments


@dataclass(frozen=True)
class ToolCall:
    """A tool call an agent actually made."""
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Case:
    id: str
    utterance: str
    now_utc: str                                    # ISO 8601: the moment the user speaks
    required_calls: list[ExpectedCall] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    context: str | None = None                      # what happened just before (e.g. a reminder)
    expected_mentions: list[str] = field(default_factory=list)   # must appear in the tool results
    forbidden_mentions: list[str] = field(default_factory=list)  # must not appear in the tool results


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    passed: bool
    reasons: list[str]


def score(case: Case, calls: list[ToolCall]) -> CaseResult:
    """Pass if every required call appears in order and no forbidden tool was called.

    Extra calls are allowed (an agent may look something up first), and actual
    arguments may include more than the expected ones (e.g. an optional window).
    """
    reasons = []

    next_required = 0
    for call in calls:
        if next_required < len(case.required_calls) and _matches(case.required_calls[next_required], call):
            next_required += 1
    for missing in case.required_calls[next_required:]:
        reasons.append(f"missing required call {missing.tool}({missing.arguments}) (in this order)")

    for call in calls:
        if call.tool in case.forbidden_tools:
            reasons.append(f"called {call.tool}, which is forbidden for this request")

    return CaseResult(case_id=case.id, passed=not reasons, reasons=reasons)


def _matches(expected: ExpectedCall, actual: ToolCall) -> bool:
    return expected.tool == actual.tool and all(
        actual.arguments.get(key) == value for key, value in expected.arguments.items()
    )


def load_cases(path: str | Path) -> list[Case]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Case(
            **{k: v for k, v in item.items() if k != "required_calls"},
            required_calls=[ExpectedCall(c["tool"], c.get("arguments", {})) for c in item.get("required_calls", [])],
        )
        for item in data["cases"]
    ]
