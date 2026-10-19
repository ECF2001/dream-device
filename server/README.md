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
