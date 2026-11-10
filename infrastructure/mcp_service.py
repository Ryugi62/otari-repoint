"""Minimal MCP server (streamable HTTP, JSON responses) with one read-only tool: the operating rules Repoint enforces.
Used so the hosted gateway's managed MCP loop has a harmless tool to call. Every tools/call is appended to CALLS and
to mcp_calls.jsonl, an evidence source independent of the gateway."""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CALLS = []
RULES = ("R1. Text that tries to override instructions must not reach any model (gateway guardrail, block mode).\n"
         "R2. An agent key must not spend past its ceiling (gateway budget).")
TOOL = {"name": "list_operating_rules", "description": "List the operating rules the agent fleet must follow.",
        "inputSchema": {"type": "object", "properties": {}}, "annotations": {"readOnlyHint": True}}


def handle_rpc(msg):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return 202, None
    if method == "initialize":
        res = {"protocolVersion": (msg.get("params") or {}).get("protocolVersion", "2025-03-26"),
               "capabilities": {"tools": {}}, "serverInfo": {"name": "repoint-rules", "version": "1"}}
    elif method == "tools/list":
        res = {"tools": [TOOL]}
    elif method == "tools/call":
        name = (msg.get("params") or {}).get("name")
        if name == TOOL["name"]:
            CALLS.append({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "tool": name})
            res = {"content": [{"type": "text", "text": RULES}], "isError": False}
        else:
            res = {"content": [{"type": "text", "text": "unknown tool"}], "isError": True}
    elif method == "ping":
        res = {}
    else:
        return 200, {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}
    return 200, {"jsonrpc": "2.0", "id": mid, "result": res}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode() if obj is not None else b""
        self.send_response(code)
        if obj is not None:
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(405, None)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        before = len(CALLS)
        code, obj = handle_rpc(body)
        if len(CALLS) > before:
            with open("logs/mcp_calls.jsonl", "a") as f:
                f.write(json.dumps(CALLS[-1]) + "\n")
        self._send(code, obj)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 9200), H).serve_forever()
