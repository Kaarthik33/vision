"""Claude via the Anthropic Messages API."""

from __future__ import annotations

from .base import Message, Provider, ProviderError, ToolCall, post_json

API_URL = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, max_tokens: int = 1024):
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set.")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens

    def chat(self, system, messages, tools):
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": to_anthropic(messages),
        }
        if tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]
        data = post_json(
            API_URL,
            payload,
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        return from_anthropic(data)


def to_anthropic(messages: list[Message]) -> list[dict]:
    out: list[dict] = []
    for msg in messages:
        if msg.role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": msg.tool_call_id,
                "content": msg.text,
            }
            # All results for one assistant turn go in a single user message.
            if out and out[-1]["role"] == "user" and _is_tool_results(out[-1]):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
        elif msg.role == "assistant":
            blocks: list[dict] = []
            if msg.text:
                blocks.append({"type": "text", "text": msg.text})
            for call in msg.tool_calls:
                blocks.append(
                    {"type": "tool_use", "id": call.id, "name": call.name, "input": call.args}
                )
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "..."}]})
        else:
            out.append({"role": "user", "content": [{"type": "text", "text": msg.text}]})
    return out


def _is_tool_results(message: dict) -> bool:
    content = message["content"]
    return isinstance(content, list) and all(b.get("type") == "tool_result" for b in content)


def from_anthropic(data: dict) -> Message:
    text_parts, calls = [], []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_parts.append(block["text"])
        elif block.get("type") == "tool_use":
            calls.append(ToolCall(block["id"], block["name"], block.get("input") or {}))
    return Message("assistant", "".join(text_parts).strip(), calls)
