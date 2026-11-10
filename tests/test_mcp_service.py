"""The MCP sidecar speaks streamable-HTTP JSON-RPC: initialize, tools/list, tools/call; calls are counted as independent evidence."""
from infrastructure.mcp_service import handle_rpc, CALLS


def test_initialize_announces_tools_capability():
    st, obj = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}})
    assert st == 200 and obj["result"]["capabilities"]["tools"] is not None and obj["id"] == 1


def test_notification_gets_202_and_no_body():
    assert handle_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"}) == (202, None)


def test_tools_list_has_one_read_only_rules_tool():
    st, obj = handle_rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = obj["result"]["tools"]
    assert [t["name"] for t in tools] == ["list_operating_rules"] and tools[0]["annotations"]["readOnlyHint"] is True


def test_tools_call_returns_rules_and_is_counted():
    CALLS.clear()
    st, obj = handle_rpc({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "list_operating_rules", "arguments": {}}})
    text = obj["result"]["content"][0]["text"]
    assert "R1" in text and "R2" in text and obj["result"]["isError"] is False and len(CALLS) == 1


def test_unknown_tool_is_an_error_result_not_a_crash():
    st, obj = handle_rpc({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "nope"}})
    assert obj["result"]["isError"] is True
