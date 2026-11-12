"""File tools. Writing asks the user for confirmation."""

from __future__ import annotations

from pathlib import Path

MAX_CHARS = 6000


def read_file(path: str) -> str:
    text = Path(path).expanduser().read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_CHARS:
        return text[:MAX_CHARS] + f"\n... (truncated, {len(text)} characters in total)"
    return text


def write_file(path: str, content: str) -> str:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content)} characters to {target}."


def list_files(path: str = ".") -> str:
    folder = Path(path).expanduser()
    entries = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    lines = [p.name + ("/" if p.is_dir() else "") for p in entries[:200]]
    return "\n".join(lines) or "(empty folder)"


def register(registry) -> None:
    registry.register(
        "read_file", "Read a text file from this computer.",
        {"path": {"type": "string"}}, ["path"],
    )(read_file)
    registry.register(
        "write_file",
        "Create or overwrite a text file. The user is asked to confirm first.",
        {"path": {"type": "string"}, "content": {"type": "string"}},
        ["path", "content"],
        dangerous=True,
    )(write_file)
    registry.register(
        "list_files", "List the files in a folder.",
        {"path": {"type": "string", "description": "Folder path, default current folder"}},
    )(list_files)
