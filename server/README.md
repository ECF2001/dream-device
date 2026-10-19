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

## Run the MCP server

The server speaks MCP over stdio: an MCP client starts it as a subprocess. It serves one user, set with `DREAMCARE_USER_ID` (the seeded demo user is `1`). `DREAMCARE_DB` picks the database file (default `dreamcare.db`).

### Try it in MCP Inspector

[MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the official browser UI for calling a server's tools by hand. It needs Node.js. From the `server/` folder, in Git Bash:

```bash
npx @modelcontextprotocol/inspector -e DREAMCARE_USER_ID=1 -e DREAMCARE_DB="$PWD/dreamcare.db" .venv/Scripts/python -m dreamcare_mcp.server
```

### Use it from Claude Desktop

Add this to `claude_desktop_config.json`, with your real paths:

```json
{
  "mcpServers": {
    "dreamcare": {
      "command": "C:\\path\\to\\Dream-Device\\server\\.venv\\Scripts\\dreamcare-mcp.exe",
      "env": {
        "DREAMCARE_USER_ID": "1",
        "DREAMCARE_DB": "C:\\path\\to\\Dream-Device\\server\\dreamcare.db"
      }
    }
  }
}
```

### Tools

| Tool | Arguments | Returns |
|---|---|---|
| `get_due_medications` | `window_minutes` (1–120, default 15) | Doses due now in the user's local time, minus those already confirmed as taken |
| `list_medications` | `include_inactive` (default false) | All medications with their schedule |
| `confirm_intake` | `medication_id`, `status` (`taken` / `missed` / `unclear`) | The recorded intake; writes to the database |

## Evaluation set

[`evals/cases.json`](evals/cases.json) lists realistic requests in Spanish ("¿Qué me toca tomar ahora?", "Sí, ya me la tomé") with the tool calls a good agent **must** make, in order, and the tools it must **never** call. For example, asking "¿Ya me tomé la metformina hoy?" must not record an intake.

- `dreamcare_mcp.evals.score(case, calls)` grades the tool calls an agent actually made: pass or fail, with reasons. It is model-agnostic.
- `tests/test_evals.py` checks the scorer, and replays every case's expected calls against the real server, with the demo data and the case's clock, so the eval set can't drift from the server.

Running a real model against these cases is the next step (Azure AI Foundry agent).

## Modules

| Module | What it does |
|---|---|
| `schedule.py` | Pure logic: which medications are due at a given local time |
| `repository.py` | SQLite access: users, medications, intake log |
| `seed.py` | Fills a database with fictional demo data |
| `server.py` | The MCP server: the three tools, time zone conversion, stdio entry point |
| `evals.py` | Eval case format, loader, and the scorer for an agent's tool calls |
