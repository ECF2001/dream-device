"""Smoke test: proves the package installs and the test pipeline (local and CI) runs."""

import re

import dreamcare_mcp


def test_package_has_semantic_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+", dreamcare_mcp.__version__)
