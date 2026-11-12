"""Configuration, read from environment variables and an optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3.1",
}

API_KEY_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama": None,  # local, no key needed
}

SYSTEM_PROMPT = (
    "You are Vision, a helpful voice assistant. Your answers are spoken aloud, "
    "so keep them short, natural and free of markdown, lists and emoji unless "
    "the user asks for detail. Use the available tools whenever they help you "
    "give an accurate answer or carry out a task, and say plainly when "
    "something cannot be done."
)


def load_dotenv(path: str | os.PathLike = ".env") -> None:
    """Load KEY=VALUE pairs from a .env file without overriding real env vars."""
    file = Path(path)
    if not file.is_file():
        return
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class Config:
    provider: str = "ollama"
    model: str = ""
    api_key: str = ""
    wake_word: str = "vision"
    use_wake_word: bool = True
    language: str = "en-US"
    voice_rate: int = 180
    max_steps: int = 8
    max_history: int = 40
    auto_approve: bool = False
    memory_file: str = str(Path.home() / ".vision" / "memory.json")
    ollama_url: str = "http://localhost:11434"
    system_prompt: str = SYSTEM_PROMPT

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()
        env = os.environ
        provider = env.get("VISION_PROVIDER", "").lower() or _detect_provider()
        if provider not in DEFAULT_MODELS:
            raise ValueError(
                f"Unknown provider '{provider}'. Choose one of: "
                + ", ".join(DEFAULT_MODELS)
            )
        key_var = API_KEY_VARS[provider]
        cfg = cls(
            provider=provider,
            model=env.get("VISION_MODEL") or DEFAULT_MODELS[provider],
            api_key=env.get(key_var, "") if key_var else "",
            wake_word=env.get("VISION_WAKE_WORD", "vision").lower(),
            language=env.get("VISION_LANGUAGE", "en-US"),
            voice_rate=int(env.get("VISION_VOICE_RATE", "180")),
            ollama_url=env.get("OLLAMA_URL", "http://localhost:11434"),
        )
        if env.get("VISION_MEMORY_FILE"):
            cfg.memory_file = env["VISION_MEMORY_FILE"]
        return cfg


def _detect_provider() -> str:
    """Pick the first provider that has an API key set, else local Ollama."""
    for name, var in API_KEY_VARS.items():
        if var and os.environ.get(var):
            return name
    return "ollama"
