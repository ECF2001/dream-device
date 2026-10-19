# DreamCare MCP server

A Model Context Protocol server that gives an AI agent medication tools for the Dream Device assistant. Work in progress; see the design in [../docs/mcp-design.md](../docs/mcp-design.md).

## Run the tests

```bash
cd server
python -m venv .venv
.venv/Scripts/activate        # Windows (Git Bash); on Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Create a demo database

```bash
python -m dreamcare_mcp.seed            # creates dreamcare.db (git-ignored)
python -m dreamcare_mcp.seed --reset    # delete and recreate it
```

The demo data is fictional.

## Modules

| Module | What it does |
|---|---|
| `schedule.py` | Pure logic: which medications are due at a given local time |
| `repository.py` | SQLite access: users, medications, intake log |
| `seed.py` | Fills a database with fictional demo data |
