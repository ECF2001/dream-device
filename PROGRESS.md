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
- [ ] Revoke the leaked OpenAI key (from the old `DreamInCode/.env`). This is the only leaked secret that may still work.
- [x] Azure SQL: the server no longer exists (its name does not resolve in DNS, checked 2026-10-19), so the leaked database credentials are dead. The Picovoice key is dead with the deleted account.
- [x] Backend: build the database connection string from `DB_*` variables; load `.env` at startup (2026-10-19, local branch `phase1/env-config` in DreamInCode-MCP).
- [x] Backend: fixed `.env` format (values only). The connection test showed the server is gone.
- [x] Scanned git history for secrets and cleaned it (2026-10-19): one Picovoice key, replaced with `REMOVED_PICOVOICE_KEY` in all 64 commits using `git filter-repo`. No other secrets found. Backup bundle in `../backups/` (contains the old key: keep local, delete when no longer needed). Removed the `team` remote so old history can't come back by accident.
- [ ] Create my personal GitHub repo, push, and see CI run.
- [ ] English README with an architecture diagram; keep the Spanish one as `README.es.md`.
- [ ] Ignore editor folders (`.vscode/`, `.idea/`) and `__pycache__/`.

Later:
- [ ] Wake word: test openWakeWord on the Pi Zero 2 (CPU use, detection) with a ready-made model.
- [ ] Wake word: put detection behind a small interface so the engine is swappable and testable.
- [ ] Wake word: train a custom "Hey Dream" model and remove Porcupine.
- [ ] Phases 2 + 3 merged: build my own DreamCare MCP server test-first (pytest + GitHub Actions CI), then connect an Azure AI Foundry agent. Design: [docs/mcp-design.md](docs/mcp-design.md) (approved 2026-10-19).
  - [x] Step 1: `server/` skeleton, one passing test, GitHub Actions workflow (2026-10-19). The workflow has not run on GitHub yet; add the status badge once the repo is on my account.
  - [ ] Step 2: `schedule.py`, test-first.

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
- **Vendor lock-in is a real risk.** The core feature depended on an outside account I did not control.
