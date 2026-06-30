"""Unit tests for response envelopes and serializers."""

import math

import olca_schema as o
from openlca_ipc.agent.errors import ImpactMethodNotFound
from openlca_ipc.contributions import TreeNode, ContributionItem

from src import responses
from tests.conftest import payload


def test_success_envelope():
    body = payload(responses.success({"count": 3}))
    assert body == {"success": True, "count": 3}


def test_error_envelope_from_olca_error():
    body = payload(responses.error(ImpactMethodNotFound(message="nope")))
    assert body["success"] is False
    assert body["is_error"] is True
    assert body["error_code"] == "IMPACT_METHOD_NOT_FOUND"
    assert body["recoverable"] is True
    assert body["suggested_next_actions"] == ["search_impact_methods"]


def test_error_envelope_from_generic_exception():
    body = payload(responses.error(ValueError("bad"), error_code="CALCULATION_FAILED"))
    assert body["success"] is False
    assert body["error_code"] == "CALCULATION_FAILED"
    assert body["recoverable"] is False


def test_legacy_content_adapts_to_call_tool_result():
    legacy = responses.success({"count": 3})
    result = responses.to_call_tool_result(legacy)
    assert result.isError is False
    assert result.structuredContent == {"success": True, "count": 3}
    assert payload(result) == {"success": True, "count": 3}


def test_ref_to_dict():
    ref = o.Ref(id="x", name="Steel")
    assert responses.ref_to_dict(ref) == {"id": "x", "name": "Steel"}
    assert responses.ref_to_dict(None) is None
    assert responses.ref_to_dict({"id": "y"}) == {"id": "y"}


def test_tree_and_contribution_serialization():
    child = TreeNode(name="B", amount=1.0, direct=1.0, share=0.4, ref=o.Ref(id="b", name="B"))
    root = TreeNode(name="A", amount=2.5, direct=1.5, share=1.0,
                    ref=o.Ref(id="a", name="A"), children=[child])
    d = responses.tree_to_dict(root)
    assert d["name"] == "A"
    assert d["children"][0]["name"] == "B"
    assert d["ref"] == {"id": "a", "name": "A"}

    item = ContributionItem(name="P", amount=2.0, share=0.8, ref=o.Ref(id="p", name="P"))
    cd = responses.contribution_to_dict(item)
    assert cd == {"name": "P", "amount": 2.0, "share": 0.8, "ref": {"id": "p", "name": "P"}}


def test_nan_share_becomes_null():
    node = TreeNode(name="A", amount=0.0, direct=0.0, share=math.nan, ref=None)
    body = payload(responses.success({"tree": [responses.tree_to_dict(node)]}))
    # NaN must serialize to null, not the invalid JSON token NaN.
    assert body["tree"][0]["share"] is None
