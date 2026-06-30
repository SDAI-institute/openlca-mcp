"""
Shared fixtures for the openLCA MCP test suite.

All tests are mocked — they patch ``src.handlers.get_client`` to return a
``MagicMock`` standing in for the OLCAClient, so no running openLCA server is
needed. The real agent-layer helpers (ResultSummary, CalculationContext,
EntitySummary, OLCAError) run against this fake data.
"""

import json
from unittest.mock import MagicMock

import pytest
import olca_schema as o

import src.handlers as handlers
from src.result_store import store


@pytest.fixture(autouse=True)
def _clean_store():
    """Ensure the result registry is empty around every test."""
    store.dispose_all()
    yield
    store.dispose_all()


@pytest.fixture
def fake_client():
    """A MagicMock OLCAClient with the attributes handlers touch."""
    client = MagicMock(name="OLCAClient")
    client.port = 8080
    client.test_connection.return_value = True
    return client


@pytest.fixture
def patch_client(fake_client, monkeypatch):
    """Patch get_client so handlers use the fake client. Returns the fake."""
    monkeypatch.setattr(handlers, "get_client", lambda: fake_client)
    return fake_client


@pytest.fixture
def gw_category():
    return o.Ref(id="GW", name="Climate change")


@pytest.fixture
def sample_impacts(gw_category):
    """Impact dicts shaped like ResultsAnalyzer.get_total_impacts()."""
    return [
        {"name": "Climate change", "category": gw_category, "amount": 2.5, "unit": "kg CO2 eq"},
        {
            "name": "Acidification",
            "category": o.Ref(id="AC", name="Acidification"),
            "amount": 0.3,
            "unit": "mol H+ eq",
        },
    ]


def payload(result):
    """Parse the JSON body of either legacy content lists or CallToolResult."""
    contents = result.content if hasattr(result, "content") else result
    assert isinstance(contents, list) and contents
    return json.loads(contents[0].text)
