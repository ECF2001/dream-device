# Progress

Working log for the Dream Device improvement project. Newest entries on top.

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-19 | Replace Porcupine (Picovoice) with **openWakeWord** | The Picovoice account was deleted by Picovoice and cannot be reactivated. An open-source engine needs no account or key, so nothing can leak or expire. |
| 2026-10-19 | Keeping the device working is **not** a priority right now | No deadline. Learning and clean design come first; the device may not run until the new wake word engine is in. |
| 2026-10-19 | This repo becomes my personal repo | The original lives in the DreamInCode-CR org. The old remote is renamed `team`; a new GitHub repo under my account will become `origin` (not created yet). |
| 2026-10-19 | Rebuild the medication backend as my own real **MCP server** (SQLite, test-first) instead of patching the team backend | Fully my own work, real Model Context Protocol, and the old Azure SQL server no longer exists anyway. |
| 2026-10-19 | Backend (team code) will be copied into a `backend/` folder, clearly labeled | Keep a clear line between team code and my own work. |

## Done

- **2026-10-19**: Inventoried the three folders and found leaked secrets (Picovoice key in `dream.py`, database credentials in the backend, an OpenAI key in the old backend's `.env`).
- **2026-10-19**: `dream.py` reads `PICOVOICE_ACCESS_KEY` and `API_BASE_URL` from the environment / `.env`, and fails fast with a clear error if one is missing. Added `.env.example`.

## Next

Phase 1 (safety and cleanup):
- [x] Revoked all OpenAI keys (2026-10-19). Every leaked secret is now dead.
- [x] Azure SQL: the server no longer exists (its name does not resolve in DNS, checked 2026-10-19), so the leaked database credentials are dead. The Picovoice key is dead with the deleted account.
- [x] Backend: build the database connection string from `DB_*` variables; load `.env` at startup (2026-10-19, local branch `phase1/env-config` in DreamInCode-MCP).
- [x] Backend: fixed `.env` format (values only). The connection test showed the server is gone.
- [x] Scanned git history for secrets and cleaned it (2026-10-19): one Picovoice key, replaced with `REMOVED_PICOVOICE_KEY` in all 64 commits using `git filter-repo`. No other secrets found. Backup bundle in `../backups/` (contains the old key: keep local, delete when no longer needed). Removed the `team` remote so old history can't come back by accident.
- [x] Created my personal repo [ECF2001/dream-device](https://github.com/ECF2001/dream-device) and opened PR #1 (2026-10-19).
- [x] CI green; merged PR #1 (skeleton) and PR #2 (actions v7, no `paths:` filter, badge).
- [x] Protected `main` with a ruleset (2026-10-19): PR required (0 approvals, solo repo), checks `test (3.11/3.12/3.13)` required, no force pushes, no deletion, no bypass.
- [ ] English README with an architecture diagram; keep the Spanish one as `README.es.md`.
- [ ] Ignore editor folders (`.vscode/`, `.idea/`) and `__pycache__/`.

Later:
- [ ] Wake word: test openWakeWord on the Pi Zero 2 (CPU use, detection) with a ready-made model.
- [ ] Wake word: put detection behind a small interface so the engine is swappable and testable.
- [ ] Wake word: train a custom "Hey Dream" model and remove Porcupine.
- [ ] Phases 2 + 3 merged: build my own DreamCare MCP server test-first (pytest + GitHub Actions CI), then connect an Azure AI Foundry agent. Design: [docs/mcp-design.md](docs/mcp-design.md) (approved 2026-10-19).
  - [x] Step 1: `server/` skeleton, one passing test, GitHub Actions workflow (2026-10-19). The workflow has not run on GitHub yet; add the status badge once the repo is on my account.
  - [x] Step 2: `schedule.py`, test-first (2026-10-19). 14 tests: time window, inactive, weekdays, date range (parametrized), windows crossing midnight, sorting. Time zone conversion moves to the tools layer (step 4), where the user's zone is known.
  - [x] Step 3: `repository.py` (SQLite schema, users, medications, intake log) and `seed.py` (fictional demo data), with 17 tests using in-memory database and `tmp_path` fixtures (2026-10-19).
  - [ ] Step 4: `server.py` with the three MCP tools (FastMCP); time zone conversion; try it with MCP Inspector.

## What I learned

- **Rotation beats cleanup.** Once a secret is in a public repo, deleting it from code does not help; only making the old value useless (rotate/revoke) does. Reverting a commit does not remove it from history either.
- **Environment variables + `.env.example`.** Code is shared, secrets are per machine. `.env` holds real values and is git-ignored; `.env.example` documents which settings exist.
- **Fail fast.** Check required settings at startup and name what is missing (never the value), instead of failing later with a confusing error.
- **Import-time side effects.** `mcp/openai_client.py` creates the OpenAI client when it is imported, so `.env` must be loaded before that import, not inside `create_app()`.
- **ODBC connection strings.** Values like passwords are wrapped in `{}` (with `}` doubled) so special characters don't break the string.
- **`pyproject.toml` and editable installs.** `pip install -e ".[dev]"` installs my package so tests import it like a real user would, plus the `dev` extras (pytest) that production doesn't need.
- **A smoke test proves the pipeline, not the logic.** The first test only checks the package imports; its job is to show that install, test discovery and CI all work before real tests arrive.
- **CI basics.** The workflow runs on push and pull request only when `server/` changes, tests three Python versions in a matrix, and has read-only permissions.
- **Rewriting history.** `git filter-repo --replace-text` rewrites every commit, so all commit hashes change. Back up first (`git bundle`), verify afterwards, and only rewrite history nobody else depends on. It does not help for copies already public (the team repo), which is why rotation comes first.
- **Test-first loop (red, green, refactor).** Decide the interface, write a test that fails, write only enough code to pass it, then clean up. Every branch of logic exists because a test demanded it.
- **Test helpers.** A fixed `NOW` keeps tests independent of the real clock; a `make_med(**overrides)` factory makes each test show only the field it is about.
- **Change one thing per test.** Start from a case that passes and change a single input, so a failure points at exactly one rule (and the test can't pass for the wrong reason).
- **Guard tests.** Some tests pass immediately (listed weekday, weekday rules across midnight, sorting); they exist to catch a future change that is too strict or subtly wrong.
- **`pytest.mark.parametrize`.** One test function, a table of cases with readable `ids`; boundaries (on start date, on end date) are where bugs hide.
- **Midnight.** A window around 00:05 includes yesterday's 23:55 dose, which must follow yesterday's weekday and date rules.
- **pytest fixtures.** A fixture prepares what a test needs (a fresh in-memory database); `yield` splits setup from cleanup; fixtures can use other fixtures (`user_id` uses `repo`). Built-ins like `tmp_path` and `capsys` give a temp folder and captured output.
- **Mutation check.** When "red" was only "module missing", deliberately break the code (`AND` → `OR` in the ownership query) to prove the important test really fails.
- **Data access boundary.** Only `repository.py` knows SQL; it converts text columns to Python types, enforces ownership (a user can't log intake on another user's medication), and never hides database errors.
- **Vendor lock-in is a real risk.** The core feature depended on an outside account I did not control.
