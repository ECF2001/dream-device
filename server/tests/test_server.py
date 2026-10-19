"""Tests for dreamcare_mcp.server, through a real MCP client.

`Client(server)` connects to the server in-process: every call goes through the
MCP protocol (tool listing, argument validation, structured results, errors)
exactly as Claude Desktop or a Foundry agent would see it, but without a network.

The clock is fixed at 14:00 UTC, which is 08:00 in Costa Rica (UTC-6, no DST).
"""

import datetime as dt

import pytest
from mcp import Client

from dreamcare_mcp.schedule import WEEKDAYS
from dreamcare_mcp.server import create_server, main

pytestmark = pytest.mark.anyio   # every test in this file is async

EVERY_DAY = frozenset(WEEKDAYS)
NOW_UTC = dt.datetime(2026, 10, 19, 14, 0, tzinfo=dt.timezone.utc)   # Monday 08:00 in Costa Rica


def fixed_clock():
    return NOW_UTC


@pytest.fixture
def user_id(repo):
    uid = repo.add_user(name="Test User", time_zone="America/Costa_Rica")
    repo.add_medication(uid, name="Metformina", dose="850 mg", time=dt.time(8, 0), days=EVERY_DAY)
    repo.add_medication(uid, name="Losartán", dose="50 mg", time=dt.time(20, 0), days=EVERY_DAY)
    repo.add_medication(uid, name="Stopped", time=dt.time(8, 5), days=EVERY_DAY, active=False)
    return uid


@pytest.fixture
def server(repo, user_id):
    return create_server(repo, user_id, clock=fixed_clock)


async def call(server, tool, arguments=None):
    async with Client(server) as client:
        return await client.call_tool(tool, arguments or {})


# --- tool listing -----------------------------------------------------------

async def test_server_exposes_exactly_the_three_tools_with_descriptions(server):
    async with Client(server) as client:
        tools = (await client.list_tools()).tools

    assert sorted(t.name for t in tools) == ["confirm_intake", "get_due_medications", "list_medications"]
    assert all(t.description for t in tools)


# --- get_due_medications ----------------------------------------------------

async def test_due_medications_uses_the_users_local_time(server):
    result = await call(server, "get_due_medications")

    assert not result.is_error
    [due] = result.structured_content["result"]
    assert due["name"] == "Metformina"
    assert due["scheduled_time"] == "08:00"
    assert due["scheduled_at"] == "2026-10-19T08:00:00-06:00"


async def test_dose_already_confirmed_as_taken_is_not_due_again(server, repo, user_id):
    [metformina] = [m for m in repo.list_medications(user_id) if m.name == "Metformina"]
    await call(server, "confirm_intake", {"medication_id": metformina.medication_id, "status": "taken"})

    result = await call(server, "get_due_medications")

    assert result.structured_content["result"] == []


async def test_dose_confirmed_as_missed_is_still_due(server, repo, user_id):
    [metformina] = [m for m in repo.list_medications(user_id) if m.name == "Metformina"]
    await call(server, "confirm_intake", {"medication_id": metformina.medication_id, "status": "missed"})

    result = await call(server, "get_due_medications")

    assert [d["name"] for d in result.structured_content["result"]] == ["Metformina"]


@pytest.mark.parametrize("window", [0, 121])
async def test_window_outside_allowed_range_is_an_error(server, window):
    result = await call(server, "get_due_medications", {"window_minutes": window})

    assert result.is_error


async def test_database_failure_is_reported_not_hidden(server, repo):
    repo._conn.close()   # simulate the database going away

    result = await call(server, "get_due_medications")

    assert result.is_error   # never an empty "nothing due" list


# --- list_medications --------------------------------------------------------

async def test_list_medications_hides_inactive_by_default(server):
    active = await call(server, "list_medications")
    everything = await call(server, "list_medications", {"include_inactive": True})

    assert [m["name"] for m in active.structured_content["result"]] == ["Metformina", "Losartán"]
    assert [m["name"] for m in everything.structured_content["result"]] == ["Metformina", "Stopped", "Losartán"]


async def test_list_medications_returns_readable_fields(server):
    result = await call(server, "list_medications")

    metformina = result.structured_content["result"][0]
    assert metformina["time"] == "08:00"
    assert metformina["days"] == list(WEEKDAYS)
    assert metformina["dose"] == "850 mg"


# --- confirm_intake ----------------------------------------------------------

async def test_confirm_intake_writes_to_the_database(server, repo, user_id):
    [metformina] = [m for m in repo.list_medications(user_id) if m.name == "Metformina"]

    result = await call(server, "confirm_intake", {"medication_id": metformina.medication_id, "status": "taken"})

    assert not result.is_error
    assert result.structured_content["recorded"] is True
    assert result.structured_content["recorded_at"] == "2026-10-19T14:00:00+00:00"
    [intake] = repo.list_intakes(user_id)
    assert (intake.medication_id, intake.status) == (metformina.medication_id, "taken")


async def test_confirm_intake_rejects_another_users_medication(server, repo, user_id):
    other = repo.add_user(name="Other User")
    theirs = repo.add_medication(other, name="Theirs", time=dt.time(8, 0), days=EVERY_DAY)

    result = await call(server, "confirm_intake", {"medication_id": theirs.medication_id, "status": "taken"})

    assert result.is_error
    assert "not found" in result.content[0].text
    assert repo.list_intakes(other) == []


async def test_confirm_intake_rejects_unknown_status(server, repo, user_id):
    [metformina] = [m for m in repo.list_medications(user_id) if m.name == "Metformina"]

    result = await call(server, "confirm_intake", {"medication_id": metformina.medication_id, "status": "done"})

    assert result.is_error
    assert repo.list_intakes(user_id) == []


# --- startup -----------------------------------------------------------------

def test_create_server_fails_fast_for_unknown_user(repo):
    with pytest.raises(ValueError, match="user 999"):
        create_server(repo, 999)


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"DREAMCARE_USER_ID": "1"}, "does not exist"),                           # no database file
        ({"DREAMCARE_USER_ID": "abc"}, "DREAMCARE_USER_ID"),                      # not a number
        ({}, "DREAMCARE_USER_ID"),                                                # not set
    ],
    ids=["missing-db", "bad-user-id", "no-user-id"],
)
def test_main_reports_configuration_errors(tmp_path, monkeypatch, capsys, env, message):
    monkeypatch.delenv("DREAMCARE_USER_ID", raising=False)
    monkeypatch.setenv("DREAMCARE_DB", str(tmp_path / "missing.db"))
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    assert main() == 1
    assert message in capsys.readouterr().err
