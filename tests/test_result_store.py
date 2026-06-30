"""Unit tests for the result registry."""

from unittest.mock import MagicMock

from src.result_store import ResultStore


def test_add_get_dispose():
    s = ResultStore()
    result = MagicMock()
    stored = s.add(result, impacts=[{"name": "x"}])
    assert stored.result_id.startswith("res_")
    assert s.get(stored.result_id) is stored
    assert stored.result_id in s

    assert s.dispose(stored.result_id) is True
    result.dispose.assert_called_once()
    assert s.get(stored.result_id) is None
    assert s.dispose(stored.result_id) is False  # already gone


def test_dispose_all_counts_and_clears():
    s = ResultStore()
    r1, r2 = MagicMock(), MagicMock()
    s.add(r1)
    s.add(r2)
    assert s.dispose_all() == 2
    r1.dispose.assert_called_once()
    r2.dispose.assert_called_once()
    assert s.dispose_all() == 0


def test_dispose_swallows_errors():
    s = ResultStore()
    result = MagicMock()
    result.dispose.side_effect = RuntimeError("boom")
    stored = s.add(result)
    # Should not raise, and should still drop the entry.
    assert s.dispose(stored.result_id) is True
    assert stored.result_id not in s
