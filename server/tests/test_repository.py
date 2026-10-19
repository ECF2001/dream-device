"""Tests for dreamcare_mcp.repository (SQLite data access).

Fixtures used here:
- `repo`: a Repository on a brand-new in-memory database. Every test gets its own,
  so tests can't affect each other, and nothing touches the disk.
- `user_id` / `other_user_id`: users created in that database. A fixture can use
  another fixture just by naming it as a parameter.
"""

import datetime as dt

import pytest

from dreamcare_mcp.repository import Repository, UnknownMedicationError, connect, init_db
from dreamcare_mcp.schedule import Medication

RECORDED_AT = dt.datetime(2026, 10, 19, 14, 0, tzinfo=dt.timezone.utc)


@pytest.fixture
def repo():
    conn = connect(":memory:")
    init_db(conn)
    yield Repository(conn)   # the test runs here
    conn.close()             # cleanup runs after the test, even if it failed


@pytest.fixture
def user_id(repo):
    return repo.add_user(name="Test User", time_zone="America/Costa_Rica")


@pytest.fixture
def other_user_id(repo):
    return repo.add_user(name="Other User")


# --- users -----------------------------------------------------------------

def test_get_user_returns_saved_user(repo, user_id):
    user = repo.get_user(user_id)

    assert user.user_id == user_id
    assert user.name == "Test User"
    assert user.time_zone == "America/Costa_Rica"


def test_get_user_returns_none_for_unknown_id(repo):
    assert repo.get_user(999) is None


def test_new_user_defaults_to_costa_rica_time_zone(repo):
    user = repo.get_user(repo.add_user(name="Default Zone"))

    assert user.time_zone == "America/Costa_Rica"


# --- medications -------------------------------------------------------------

def test_added_medication_round_trips_with_python_types(repo, user_id):
    added = repo.add_medication(
        user_id,
        name="Losartán",
        time=dt.time(20, 30),
        days=frozenset({"mon", "wed", "fri"}),
        dose="50 mg",
        instructions="Con agua",
        start_date=dt.date(2026, 10, 1),
        end_date=dt.date(2026, 12, 31),
    )

    [loaded] = repo.list_medications(user_id)

    assert loaded == added
    assert isinstance(loaded, Medication)
    assert loaded.time == dt.time(20, 30)
    assert loaded.days == frozenset({"mon", "wed", "fri"})
    assert loaded.start_date == dt.date(2026, 10, 1)


def test_list_medications_hides_inactive_by_default(repo, user_id):
    repo.add_medication(user_id, name="Active", time=dt.time(8, 0), days=frozenset({"mon"}))
    repo.add_medication(user_id, name="Stopped", time=dt.time(9, 0), days=frozenset({"mon"}), active=False)

    names = [m.name for m in repo.list_medications(user_id)]
    all_names = [m.name for m in repo.list_medications(user_id, include_inactive=True)]

    assert names == ["Active"]
    assert all_names == ["Active", "Stopped"]


def test_list_medications_only_returns_that_users_medications(repo, user_id, other_user_id):
    repo.add_medication(other_user_id, name="Not yours", time=dt.time(8, 0), days=frozenset({"mon"}))

    assert repo.list_medications(user_id) == []


def test_add_medication_rejects_unknown_weekday(repo, user_id):
    with pytest.raises(ValueError, match="days"):
        repo.add_medication(user_id, name="Typo", time=dt.time(8, 0), days=frozenset({"monday"}))


# --- intake log --------------------------------------------------------------

def test_record_intake_stores_a_row(repo, user_id):
    med = repo.add_medication(user_id, name="Metformina", time=dt.time(8, 0), days=frozenset({"mon"}))

    intake = repo.record_intake(user_id, med.medication_id, "taken", RECORDED_AT)

    assert intake.medication_id == med.medication_id
    assert intake.status == "taken"
    assert intake.recorded_at == RECORDED_AT
    assert repo.list_intakes(user_id) == [intake]


def test_record_intake_rejects_another_users_medication(repo, user_id, other_user_id):
    theirs = repo.add_medication(other_user_id, name="Theirs", time=dt.time(8, 0), days=frozenset({"mon"}))

    with pytest.raises(UnknownMedicationError):
        repo.record_intake(user_id, theirs.medication_id, "taken", RECORDED_AT)

    assert repo.list_intakes(other_user_id) == []   # nothing was written


@pytest.mark.parametrize("bad_status", ["done", "", "TAKEN"])
def test_record_intake_rejects_invalid_status(repo, user_id, bad_status):
    med = repo.add_medication(user_id, name="Metformina", time=dt.time(8, 0), days=frozenset({"mon"}))

    with pytest.raises(ValueError, match="status"):
        repo.record_intake(user_id, med.medication_id, bad_status, RECORDED_AT)


def test_record_intake_requires_timezone_aware_time(repo, user_id):
    med = repo.add_medication(user_id, name="Metformina", time=dt.time(8, 0), days=frozenset({"mon"}))

    with pytest.raises(ValueError, match="time zone"):
        repo.record_intake(user_id, med.medication_id, "taken", dt.datetime(2026, 10, 19, 8, 0))
