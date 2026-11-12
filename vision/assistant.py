"""The core loop: user text in, model + tools, answer text out."""

from __future__ import annotations

from typing import Callable

from .config import Config
from .providers import Message, Provider
from .tools import ToolRegistry


class Assistant:
    def __init__(
        self,
        provider: Provider,
        tools: ToolRegistry,
        config: Config | None = None,
        confirm: Callable[[str], bool] | None = None,
        on_tool: Callable[[str, dict], None] | None = None,
    ):
        self.provider = provider
        self.tools = tools
        self.config = config or Config()
        self.confirm = confirm
        self.on_tool = on_tool
        self.history: list[Message] = []

    def ask(self, text: str) -> str:
        """Answer one user request, running tools as needed."""
        start = len(self.history)
        self.history.append(Message("user", text))
        try:
            return self._run()
        except Exception:
            del self.history[start:]  # leave no half-finished turn behind
            raise

    def _run(self) -> str:
        for _ in range(self.config.max_steps):
            reply = self.provider.chat(
                self.config.system_prompt, self.history, self.tools.schemas()
            )
            self.history.append(reply)
            if not reply.tool_calls:
                self._trim()
                return reply.text or "Done."
            for call in reply.tool_calls:
                if self.on_tool:
                    self.on_tool(call.name, call.args)
                confirm = (lambda q: True) if self.config.auto_approve else self.confirm
                result = self.tools.run(call.name, call.args, confirm)
                self.history.append(
                    Message("tool", result, tool_call_id=call.id, name=call.name)
                )
        self._trim()
        return "Sorry, that took too many steps and I had to stop."

    def reset(self) -> None:
        self.history.clear()

    def _trim(self) -> None:
        """Drop the oldest turns, always cutting at a user message so that
        tool calls and their results are never separated."""
        while len(self.history) > self.config.max_history:
            for i in range(1, len(self.history)):
                if self.history[i].role == "user":
                    del self.history[:i]
                    break
            else:
                return
