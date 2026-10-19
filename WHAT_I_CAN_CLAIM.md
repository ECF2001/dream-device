# What I can claim

An honest list of what I (Emilio Conejo, GitHub `ECF2001`) personally built, so the README, my resume and interviews stay accurate. Updated as work is finished.

## Original project: ExpoCenfo 2025 (team of three)

**My role:** edge development engineer and team coordinator. Samuel was the AI engineer (backend), Sebastián the application engineer.

### Built by me: the device software (`dream.py`), 2025-07-30 to 2025-08-20
Evidence: all 59 commits from that period in this repo are mine (58 as `ECF2001`, 1 as `Emilio Conejo`).

- Wake word detection with Porcupine ("Hey Dream") on a Raspberry Pi Zero 2
- Voice activity detection with noise calibration, and automatic speech capture
- Audio playback for WAV and MP3, with an FFmpeg fallback
- Speech-to-text and text-to-speech calls to the team backend
- Local yes/no classification of spoken confirmations
- Medication fetching and an automatic reminder poller, with a lock against repeated reminders
- Conversation flow with follow-up questions
- `test.py`, a small mock upload server used during development
- Set up the team's GitHub repositories

### Not mine (team code)
- The Flask backend (`DreamInCode-MCP`, `DreamInCode`): API endpoints, OpenAI integration, Azure SQL queries, Azure deployment workflow. Written by Samuel, with documentation by Sebastián.
- "MCP" in the backend means *Multi-Channel Processor*, not Model Context Protocol.

## Improvement project (2026, ongoing)

Work done with an AI coding assistant (Claude Code). I decide the plan, review every change, and write key parts myself; the notes below say who wrote what.

| Date | What | Who wrote it |
|---|---|---|
| 2026-10-19 | Audited the three repos for leaked secrets and risky files | Me, guided by the assistant |
| 2026-10-19 | Moved the Picovoice key and backend URL in `dream.py` to environment variables (`python-dotenv`), added `.env.example` | I wrote the env variable reading and `load_dotenv()`; the assistant wrote the fail-fast check, which I reviewed |
| 2026-10-19 | Decided to replace Porcupine with openWakeWord | My decision, after comparing options |
