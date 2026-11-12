"""Offline tests: no network, microphone or API key needed."""

import json

import pytest

from vision.assistant import Assistant
from vision.config import Config
from vision.providers import Message, Provider, ProviderError, ToolCall
from vision.providers.anthropic import from_anthropic, to_anthropic
from vision.providers.openai_compat import from_openai, to_openai
from vision.speech import strip_wake_word
from vision.tools import build_registry
from vision.tools.system import calculate


class ScriptedProvider(Provider):
    """Replays a fixed list of assistant messages and records what it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.seen = []

    def chat(self, system, messages, tools):
        self.seen.append(list(messages))
        return self.replies.pop(0)


@pytest.fixture
def config(tmp_path):
    return Config(memory_file=str(tmp_path / "memory.json"))


def test_calculator():
    assert calculate("2 * (3 + 4)") == 14
    assert calculate("2^10") == 1024
    assert round(calculate("sqrt(16) + pi"), 3) == 7.142
    for bad in ("__import__('os').system('ls')", "open('x')", "9**9**9"):
        with pytest.raises(Exception):
            calculate(bad)


def test_wake_word():
    assert strip_wake_word("hey Vision, what time is it", "vision") == "what time is it"
    assert strip_wake_word("vision", "vision") == ""
    assert strip_wake_word("what time is it", "vision") is None
    assert strip_wake_word("television is on", "vision") is None


def test_plain_answer(config):
    provider = ScriptedProvider([Message("assistant", "Hello!")])
    assistant = Assistant(provider, build_registry(config), config)
    assert assistant.ask("hi") == "Hello!"


def test_tool_round_trip(config):
    provider = ScriptedProvider([
        Message("assistant", "", [ToolCall("c1", "calculate", {"expression": "6*7"})]),
        Message("assistant", "It is 42."),
    ])
    assistant = Assistant(provider, build_registry(config), config)
    assert assistant.ask("what is six times seven") == "It is 42."
    tool_message = provider.seen[1][-1]
    assert (tool_message.role, tool_message.text, tool_message.tool_call_id) == ("tool", "42", "c1")


def test_dangerous_tool_needs_confirmation(config, tmp_path):
    target = tmp_path / "note.txt"
    call = ToolCall("c1", "write_file", {"path": str(target), "content": "hi"})

    def run(confirm):
        provider = ScriptedProvider([Message("assistant", "", [call]), Message("assistant", "ok")])
        Assistant(provider, build_registry(config), config, confirm=confirm).ask("write it")
        return provider.seen[1][-1].text

    assert "did not allow" in run(lambda q: False)
    assert not target.exists()
    assert "did not allow" in run(None)
    assert "Wrote 2 characters" in run(lambda q: True)
    assert target.read_text() == "hi"


def test_tool_errors_are_reported_not_raised(config):
    tools = build_registry(config)
    assert tools.run("nope", {}).startswith("Error: unknown tool")
    assert tools.run("calculate", {"wrong": 1}).startswith("Error: bad arguments")
    assert tools.run("read_file", {"path": "/does/not/exist"}).startswith("Error:")


def test_memory(config):
    tools = build_registry(config)
    assert tools.run("recall", {}) == "Nothing saved about that."
    tools.run("remember", {"note": "My bike lock code is blue"})
    assert "bike lock" in tools.run("recall", {"query": "bike"})
    assert tools.run("recall", {"query": "passport"}) == "Nothing saved about that."


def test_step_limit(config):
    config.max_steps = 3
    loop = [Message("assistant", "", [ToolCall(f"c{i}", "get_time", {})]) for i in range(3)]
    assistant = Assistant(ScriptedProvider(loop), build_registry(config), config)
    assert "too many steps" in assistant.ask("loop forever")


def test_history_trim_keeps_tool_pairs(config):
    config.max_history = 4
    replies = []
    for i in range(5):
        replies += [
            Message("assistant", "", [ToolCall(f"c{i}", "get_time", {})]),
            Message("assistant", "done"),
        ]
    assistant = Assistant(ScriptedProvider(replies), build_registry(config), config)
    for _ in range(5):
        assistant.ask("time?")
    assert assistant.history[0].role == "user"
    assert len(assistant.history) <= 4


HISTORY = [
    Message("user", "weather and time?"),
    Message("assistant", "Checking.", [
        ToolCall("a", "weather", {"city": "Berlin"}),
        ToolCall("b", "get_time", {}),
    ]),
    Message("tool", "sunny", tool_call_id="a", name="weather"),
    Message("tool", "noon", tool_call_id="b", name="get_time"),
]


def test_anthropic_format():
    out = to_anthropic(HISTORY)
    assert [m["role"] for m in out] == ["user", "assistant", "user"]
    assert [b["type"] for b in out[1]["content"]] == ["text", "tool_use", "tool_use"]
    assert [b["tool_use_id"] for b in out[2]["content"]] == ["a", "b"]
    reply = from_anthropic({"content": [
        {"type": "text", "text": "Sure."},
        {"type": "tool_use", "id": "x", "name": "get_time", "input": {}},
    ]})
    assert reply.text == "Sure." and reply.tool_calls[0].name == "get_time"


def test_openai_format():
    out = to_openai(HISTORY)
    assert [m["role"] for m in out] == ["user", "assistant", "tool", "tool"]
    assert json.loads(out[1]["tool_calls"][0]["function"]["arguments"]) == {"city": "Berlin"}
    reply = from_openai({"content": None, "tool_calls": [
        {"id": "x", "type": "function", "function": {"name": "weather", "arguments": '{"city": "Paris"}'}},
    ]})
    assert reply.text == "" and reply.tool_calls[0].args == {"city": "Paris"}


def test_tool_schemas_are_valid(config):
    for schema in build_registry(config).schemas():
        assert schema["name"] and schema["description"]
        assert schema["parameters"]["type"] == "object"
        assert set(schema["parameters"]["required"]) <= set(schema["parameters"]["properties"])


def test_failed_turn_is_rolled_back(config):
    class Broken(Provider):
        def chat(self, system, messages, tools):
            raise ProviderError("offline")

    assistant = Assistant(Broken(), build_registry(config), config)
    with pytest.raises(ProviderError):
        assistant.ask("hello")
    assert assistant.history == []
