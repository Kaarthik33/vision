"""Language model providers."""

from __future__ import annotations

from ..config import Config
from .anthropic import AnthropicProvider
from .base import Message, Provider, ProviderError, ToolCall
from .openai_compat import BASE_URLS, OpenAICompatProvider

__all__ = ["Message", "Provider", "ProviderError", "ToolCall", "create_provider"]


def create_provider(config: Config) -> Provider:
    name = config.provider
    if name == "anthropic":
        return AnthropicProvider(config.api_key, config.model)
    if name == "ollama":
        return OpenAICompatProvider(
            "ollama", config.ollama_url.rstrip("/") + "/v1", "ollama", config.model
        )
    if name in BASE_URLS:
        if not config.api_key:
            raise ProviderError(f"No API key set for provider '{name}'. See .env.example.")
        return OpenAICompatProvider(name, BASE_URLS[name], config.api_key, config.model)
    raise ProviderError(f"Unknown provider '{name}'.")
