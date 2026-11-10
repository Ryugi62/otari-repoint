"""Append-only jsonl sink; returns '<file>:<line>' so evidence lines can point at the full record."""
from __future__ import annotations

import json
import os
import threading


class JsonlSink:
    def __init__(self, path: str, fresh: bool = True):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.lock = threading.Lock()
        self.n = 0
        if fresh or not os.path.exists(path):
            open(path, "w").close()
        else:
            with open(path) as f:
                self.n = sum(1 for _ in f)

    def __call__(self, rec: dict) -> str:
        with self.lock:
            self.n += 1
            with open(self.path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return "%s:%d" % (os.path.basename(self.path), self.n)
