"""Tool registry: the actions Vision can take."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[..., Any]
    dangerous: bool = False  # needs the user's confirmation before running


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name, description, properties=None, required=None, dangerous=False):
        """Decorator that registers a function as a tool."""

        def wrap(func):
            self._tools[name] = Tool(
                name=name,
                description=description,
                parameters={
                    "type": "object",
                    "properties": properties or {},
                    "required": required or [],
                },
                func=func,
                dangerous=dangerous,
            )
            return func

        return wrap

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self._tools.values()
        ]

    def run(self, name: str, args: dict, confirm: Callable[[str], bool] | None = None) -> str:
        """Run a tool and always return a string result (errors included)."""
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'."
        if tool.dangerous:
            question = f"Vision wants to run {name} with {args}. Allow?"
            if confirm is None or not confirm(question):
                return "The user did not allow this action."
        try:
            result = tool.func(**(args or {}))
        except TypeError as err:
            return f"Error: bad arguments for {name}: {err}"
        except Exception as err:  # tools must never crash the assistant
            return f"Error: {type(err).__name__}: {err}"
        return str(result)


def build_registry(config=None) -> ToolRegistry:
    """Create a registry with all built-in tools."""
    from . import files, memory, system, web

    registry = ToolRegistry()
    system.register(registry)
    web.register(registry)
    files.register(registry)
    memory.register(registry, config.memory_file if config else None)
    return registry
