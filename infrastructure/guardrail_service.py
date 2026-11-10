"""Guardrail sidecar implementing the Otari guardrails contract: POST /validate.
A deterministic prompt-injection screen (phrase rules). It is NOT the ML guardrail container that Mozilla ships;
it exists so the self-hosted stack runs without downloading a classifier. Hosted Otari.ai uses its own guardrail service."""
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RULES = [
    r"ignore (all |your |any )?(previous|prior|above) (instructions|rules)",
    r"disregard (all |your )?(previous|prior) (instructions|rules)",
    r"reveal (your |the )?(system prompt|hidden instructions)",
    r"you are now (dan|in developer mode)",
    r"delete (all|every) (files|records) and do not tell",
]


def screen(text):
    t = (text or "").lower()
    hits = [r for r in RULES if re.search(r, t)]
    return {"valid": not hits, "explanation": None, "score": 0.99 if hits else 0.01}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send(200, {"status": "ok"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/validate":
            return self._send(200, {"profile": body.get("profile"), "result": screen(body.get("input_text", ""))})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(sys.argv[1]) if len(sys.argv) > 1 else 9100), H).serve_forever()
