"""Shared fixtures for FBI Crime Data MCP tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest


@dataclass
class FakeAppContext:
    """Minimal AppContext stand-in that records api_get calls."""

    api_get: AsyncMock = field(default_factory=lambda: AsyncMock(return_value='{"ok": true}'))


class FakeContext:
    """Minimal Context stand-in providing lifespan_context."""

    def __init__(self, app_ctx: FakeAppContext):
        self.lifespan_context = app_ctx


@pytest.fixture
def app_ctx():
    return FakeAppContext()


@pytest.fixture
def ctx(app_ctx):
    return FakeContext(app_ctx)
