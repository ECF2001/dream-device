# Progress

Working log for the Dream Device improvement project. Newest entries on top.

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-10-19 | Replace Porcupine (Picovoice) with **openWakeWord** | The Picovoice account was deleted by Picovoice and cannot be reactivated. An open-source engine needs no account or key, so nothing can leak or expire. |
| 2026-10-19 | Keeping the device working is **not** a priority right now | No deadline. Learning and clean design come first; the device may not run until the new wake word engine is in. |
| 2026-10-19 | This repo becomes my personal repo | The original lives in the DreamInCode-CR org. The old remote is renamed `team`; a new GitHub repo under my account will become `origin` (not created yet). |
| 2026-10-19 | Backend (team code) will be copied into a `backend/` folder, clearly labeled | Keep a clear line between team code and my own work. |

## Done

- **2026-10-19**: Inventoried the three folders and found leaked secrets (Picovoice key in `dream.py`, database credentials in the backend, an OpenAI key in the old backend's `.env`).
- **2026-10-19**: `dream.py` reads `PICOVOICE_ACCESS_KEY` and `API_BASE_URL` from the environment / `.env`, and fails fast with a clear error if one is missing. Added `.env.example`.

## Next

Phase 1 (safety and cleanup):
- [ ] Rotate the leaked credentials: OpenAI key, Azure SQL password (if the server still exists). The Picovoice key is dead with the deleted account.
- [ ] Backend: build the database connection string from `DB_*` variables; call `load_dotenv()` in `create_app()`.
- [ ] Scan git history for secrets (gitleaks) and clean it before the first push to my own repo.
- [ ] English README with an architecture diagram; keep the Spanish one as `README.es.md`.
- [ ] Ignore editor folders (`.vscode/`, `.idea/`) and `__pycache__/`.

Later:
- [ ] Wake word: test openWakeWord on the Pi Zero 2 (CPU use, detection) with a ready-made model.
- [ ] Wake word: put detection behind a small interface so the engine is swappable and testable.
- [ ] Wake word: train a custom "Hey Dream" model and remove Porcupine.
- [ ] Phase 2: pytest tests and GitHub Actions CI.
- [ ] Phase 3: Azure AI Foundry agent, real Model Context Protocol server, evaluation.

## What I learned

- **Rotation beats cleanup.** Once a secret is in a public repo, deleting it from code does not help; only making the old value useless (rotate/revoke) does. Reverting a commit does not remove it from history either.
- **Environment variables + `.env.example`.** Code is shared, secrets are per machine. `.env` holds real values and is git-ignored; `.env.example` documents which settings exist.
- **Fail fast.** Check required settings at startup and name what is missing (never the value), instead of failing later with a confusing error.
- **Vendor lock-in is a real risk.** The core feature depended on an outside account I did not control.
