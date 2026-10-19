"""Tests for dreamcare_mcp.seed (demo data).

`tmp_path` is a built-in pytest fixture: a fresh temporary folder for each test,
so the script can write a real database file without touching the project.
"""

import pytest

from dreamcare_mcp.repository import Repository, connect, init_db
from dreamcare_mcp.schedule import WEEKDAYS
from dreamcare_mcp.seed import main, seed_demo


def open_repo(path) -> Repository:
    return Repository(connect(str(path)))


def test_seed_demo_creates_one_user_with_active_medications():
    conn = connect(":memory:")
    init_db(conn)
    repo = Repository(conn)

    user_id = seed_demo(repo)

    assert repo.get_user(user_id).name.endswith("(demo)")
    meds = repo.list_medications(user_id)
    assert len(meds) >= 3
    assert all(m.days <= set(WEEKDAYS) for m in meds)


def test_main_creates_database_file(tmp_path):
    db = tmp_path / "demo.db"

    assert main(["--db", str(db)]) == 0

    assert db.exists()
    assert open_repo(db).get_user(1) is not None


def test_main_refuses_to_seed_an_existing_database(tmp_path, capsys):
    db = tmp_path / "demo.db"
    main(["--db", str(db)])

    assert main(["--db", str(db)]) == 1

    assert "--reset" in capsys.readouterr().err
    assert open_repo(db).get_user(2) is None          # no second demo user


def test_main_with_reset_starts_from_scratch(tmp_path):
    db = tmp_path / "demo.db"
    main(["--db", str(db)])

    assert main(["--db", str(db), "--reset"]) == 0

    repo = open_repo(db)
    assert repo.get_user(1) is not None
    assert repo.get_user(2) is None                   # old data is gone, not duplicated
