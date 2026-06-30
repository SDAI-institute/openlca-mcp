"""Unit tests for the openLCA IPC client wiring."""

from src.lca_client import _apply_session_timeout


class _FakeSession:
    """Minimal stand-in for a requests.Session that records the last call."""

    def __init__(self):
        self.last = {}

    def request(self, method, url, **kwargs):
        self.last = {"method": method, "url": url, **kwargs}
        return object()


class _FakeRawClient:
    def __init__(self):
        self._s = _FakeSession()


def test_apply_session_timeout_injects_default():
    raw = _FakeRawClient()
    _apply_session_timeout(raw, 12.5)

    raw._s.request("POST", "http://localhost:8080", json={"x": 1})
    assert raw._s.last["timeout"] == 12.5


def test_apply_session_timeout_preserves_explicit_timeout():
    raw = _FakeRawClient()
    _apply_session_timeout(raw, 12.5)

    raw._s.request("POST", "http://localhost:8080", timeout=3)
    assert raw._s.last["timeout"] == 3


def test_apply_session_timeout_is_idempotent():
    raw = _FakeRawClient()
    _apply_session_timeout(raw, 12.5)
    wrapped_once = raw._s.request
    _apply_session_timeout(raw, 99)  # second call must be a no-op
    assert raw._s.request is wrapped_once


def test_apply_session_timeout_tolerates_missing_session():
    class NoSession:
        _s = None

    _apply_session_timeout(NoSession(), 12.5)  # must not raise
