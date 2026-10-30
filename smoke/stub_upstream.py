"""스모크용 가짜 업스트림(0원). /<tag>/v1/chat/completions, /validate. tag a=항상 500, 나머지 정상.
도구가 선언되고 사용자 글에 FETCH/CODE 가 있으면 첫 턴에 해당 도구 호출을 낸다. 요청은 jsonl로 기록."""
import json, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LOG = sys.argv[2] if len(sys.argv) > 2 else "stub-requests.jsonl"


def log(rec):
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def pick_tool(tools, kw):
    for t in tools:
        fn = t.get("function", {})
        if kw in fn.get("name", ""):
            return fn["name"], list(fn.get("parameters", {}).get("properties", {}))
    return None, []


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        log({"t": time.time(), "GET": self.path})
        tag = self.path.split("/")[1]
        if "/models" in self.path:
            return self._send(200, {"object": "list", "data": [{"id": f"model-{tag}", "object": "model", "owned_by": tag}]})
        self._send(404, {"error": "nf"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        log({"t": time.time(), "POST": self.path, "model": body.get("model"),
             "tools": [t.get("function", {}).get("name") for t in body.get("tools", [])],
             "tool_schema": [t.get("function", {}) for t in body.get("tools", [])],
             "last": (body.get("messages") or [{}])[-1]})
        if self.path == "/validate":
            txt = body.get("input_text", "").lower()
            bad = "ignore all previous" in txt or "ignore your instructions" in txt
            return self._send(200, {"profile": body.get("profile"), "result": {"valid": not bad, "explanation": None, "score": 0.99 if bad else 0.01}})
        tag = self.path.split("/")[1]
        if tag == "a":
            return self._send(500, {"error": {"message": "stub a down", "type": "server_error"}})
        msgs = body.get("messages", [])
        last = msgs[-1] if msgs else {}
        usage = {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
        tools = body.get("tools", [])
        user_txt = " ".join(str(m.get("content")) for m in msgs if m.get("role") == "user")
        if tools and last.get("role") != "tool":
            kw = "fetch" if "FETCH" in user_txt else "code" if "CODE" in user_txt else None
            name, props = pick_tool(tools, kw) if kw else (None, [])
            if name:
                if kw == "fetch":
                    args = {"url": "https://example.com/"}
                else:
                    args = {p: ("python" if p in ("language", "lang") else "print(sum(range(1,11)))") for p in props} or {"code": "print(55)"}
                return self._send(200, {"id": "c1", "object": "chat.completion", "created": 1, "model": body.get("model"),
                    "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
                    "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}],
                    "usage": usage})
        content = f"[{tag}] answered. last={str(last.get('content'))[:400]}"
        self._send(200, {"id": "c2", "object": "chat.completion", "created": 1, "model": body.get("model"),
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}], "usage": usage})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(sys.argv[1])), H).serve_forever()
