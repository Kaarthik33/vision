"""OpenAI-compatible chat completions.

One implementation covers OpenAI, Google Gemini (through its OpenAI-compatible
endpoint) and a local Ollama server.
"""

from __future__ import annotations

import json

from .base import Message, Provider, ProviderError, ToolCall, post_json

BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}


class OpenAICompatProvider(Provider):
    def __init__(self, name: str, base_url: str, api_key: str, model: str):
        self.name = name
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.api_key = api_key
        self.model = model

    def chat(self, system, messages, tools):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + to_openai(messages),
        }
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
        data = post_json(self.url, payload, {"Authorization": f"Bearer {self.api_key}"})
        try:
            return from_openai(data["choices"][0]["message"])
        except (KeyError, IndexError) as err:
            raise ProviderError(f"Unexpected response from {self.name}: {data}") from err


def to_openai(messages: list[Message]) -> list[dict]:
    out = []
    for msg in messages:
        if msg.role == "tool":
            out.append({"role": "tool", "tool_call_id": msg.tool_call_id, "content": msg.text})
        elif msg.role == "assistant":
            item: dict = {"role": "assistant", "content": msg.text or None}
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.args)},
                    }
                    for c in msg.tool_calls
                ]
            out.append(item)
        else:
            out.append({"role": "user", "content": msg.text})
    return out


def from_openai(message: dict) -> Message:
    calls = []
    for i, call in enumerate(message.get("tool_calls") or []):
        fn = call.get("function", {})
        raw = fn.get("arguments") or "{}"
        try:
            args = raw if isinstance(raw, dict) else json.loads(raw)
        except json.JSONDecodeError:
            args = {}
        calls.append(ToolCall(call.get("id") or f"call_{i}", fn.get("name", ""), args))
    return Message("assistant", (message.get("content") or "").strip(), calls)
