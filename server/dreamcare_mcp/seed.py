"""Create a local SQLite database with fictional demo data.

Usage (from the server/ folder):
    python -m dreamcare_mcp.seed                 # creates dreamcare.db
    python -m dreamcare_mcp.seed --db other.db
    python -m dreamcare_mcp.seed --reset         # delete and recreate

All data here is made up; it does not describe a real person.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from .repository import Repository, connect, init_db
from .schedule import WEEKDAYS

EVERY_DAY = frozenset(WEEKDAYS)


def seed_demo(repo: Repository) -> int:
    """Add one fictional user with a few medications. Returns the new user's id."""
    user_id = repo.add_user(name="Rosa Jiménez (demo)")
    repo.add_medication(
        user_id, name="Metformina", dose="850 mg", instructions="Con el desayuno",
        time=dt.time(8, 0), days=EVERY_DAY,
    )
    repo.add_medication(
        user_id, name="Losartán", dose="50 mg", instructions="Con un vaso de agua",
        time=dt.time(20, 0), days=EVERY_DAY,
    )
    repo.add_medication(
        user_id, name="Vitamina D", dose="1 cápsula", instructions="Con el almuerzo",
        time=dt.time(12, 30), days=frozenset({"mon", "wed", "fri"}),
    )
    return user_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a SQLite database with fictional demo data.")
    parser.add_argument("--db", default="dreamcare.db", help="database file (default: dreamcare.db)")
    parser.add_argument("--reset", action="store_true", help="delete the database first if it exists")
    args = parser.parse_args(argv)

    db_path = Path(args.db)
    if db_path.exists():
        if not args.reset:
            print(f"{db_path} already exists. Use --reset to delete and recreate it.", file=sys.stderr)
            return 1
        db_path.unlink()

    conn = connect(str(db_path))
    try:
        init_db(conn)
        repo = Repository(conn)
        user_id = seed_demo(repo)
        meds = repo.list_medications(user_id)
    finally:
        conn.close()

    print(f"Created {db_path} with demo user {user_id} and {len(meds)} medications:")
    for med in meds:
        print(f"  {med.time:%H:%M}  {med.name} ({med.dose})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
