"""Provider-neutral message types and the provider interface."""

from __future__ import annotations

import http.client
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class Message:
    """role is 'user', 'assistant' or 'tool'."""

    role: str
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str = ""  # set on 'tool' messages
    name: str = ""  # tool name on 'tool' messages


class ProviderError(RuntimeError):
    pass


class Provider:
    """A chat model that can answer with text and/or tool calls."""

    name = "base"

    def chat(self, system: str, messages: list[Message], tools: list[dict]) -> Message:
        """Return the assistant's next message.

        `tools` is a list of {"name", "description", "parameters"} dicts where
        parameters is a JSON schema object.
        """
        raise NotImplementedError


def post_json(url: str, payload: dict, headers: dict, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:500]
        raise ProviderError(f"HTTP {err.code} from {url}: {detail}") from err
    except urllib.error.URLError as err:
        raise ProviderError(f"Could not reach {url}: {err.reason}") from err
    except (http.client.HTTPException, OSError, json.JSONDecodeError) as err:
        raise ProviderError(f"Bad response from {url}: {err!r}") from err
