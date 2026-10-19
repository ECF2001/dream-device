"""Shared pytest fixtures. pytest loads this file automatically for every test in this folder."""

import pytest

from dreamcare_mcp.repository import Repository, connect, init_db


@pytest.fixture
def repo():
    """A Repository on a brand-new in-memory database (one per test)."""
    conn = connect(":memory:")
    init_db(conn)
    yield Repository(conn)   # the test runs here
    conn.close()             # cleanup runs after the test, even if it failed


@pytest.fixture
def anyio_backend():
    """Run `@pytest.mark.anyio` tests on asyncio (the MCP SDK is built on anyio)."""
    return "asyncio"
