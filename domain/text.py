"""Answer normalization shared by every task check (pure)."""
from __future__ import annotations

import re

_THOUGHT = re.compile(r"<thought>.*?</thought>", re.S | re.I)
_FENCE = re.compile(r"^```[a-zA-Z]*\n(.*?)\n```$", re.S)


def has_thought_leak(text: str) -> bool:
    return bool(_THOUGHT.search(text or ""))


def normalize_answer(text: str) -> str:
    t = _THOUGHT.sub("", text or "").strip()
    m = _FENCE.match(t)
    return (m.group(1) if m else t).strip()
