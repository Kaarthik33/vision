"""Long-term notes that survive between sessions (stored as a local JSON file)."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


class Memory:
    def __init__(self, path: str | None = None):
        self.path = Path(path or Path.home() / ".vision" / "memory.json")

    def _load(self) -> list[dict]:
        if not self.path.is_file():
            return []
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

    def remember(self, note: str) -> str:
        notes = self._load()
        notes.append({"note": note, "saved": dt.datetime.now().isoformat(timespec="minutes")})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
        return "Saved."

    def recall(self, query: str = "") -> str:
        notes = self._load()
        words = query.lower().split()
        if words:
            notes = [n for n in notes if any(w in n["note"].lower() for w in words)]
        if not notes:
            return "Nothing saved about that."
        return "\n".join(f"- {n['note']} (saved {n['saved']})" for n in notes[-20:])


def register(registry, path: str | None = None) -> None:
    memory = Memory(path)
    registry.register(
        "remember", "Save a note or fact the user wants remembered for later.",
        {"note": {"type": "string"}}, ["note"],
    )(memory.remember)
    registry.register(
        "recall",
        "Look up previously saved notes. Leave query empty to list everything.",
        {"query": {"type": "string"}},
    )(memory.recall)
