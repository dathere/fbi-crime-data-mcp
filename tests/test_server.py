"""Tests for the server entry point."""

from unittest.mock import MagicMock

from fbi_crime_data_mcp import server


def test_main_runs_the_server(monkeypatch):
    run = MagicMock()
    monkeypatch.setattr(server.mcp, "run", run)
    server.main()
    run.assert_called_once_with()
