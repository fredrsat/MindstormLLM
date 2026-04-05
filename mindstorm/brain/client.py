"""LLM client wrapper for robot decision-making. Supports Anthropic and Ollama."""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod

log = logging.getLogger(__name__)


class Brain(ABC):
    """Abstract brain interface."""

    @abstractmethod
    async def decide(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> str: ...


class AnthropicBrain(Brain):
    """Claude via Anthropic API."""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def decide(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text


class OllamaBrain(Brain):
    """Local LLM via Ollama (OpenAI-compatible API)."""

    def __init__(self, model: str = "gemma4", url: str = "http://localhost:11434"):
        import httpx
        self.model = model
        self.url = url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)

    async def decide(
        self,
        system_prompt: str,
        messages: list[dict],
        max_tokens: int = 300,
        temperature: float = 0.3,
    ) -> str:
        # Ollama uses OpenAI-compatible chat API
        ollama_messages = [{"role": "system", "content": system_prompt}]
        ollama_messages.extend(messages)

        response = await self._client.post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]


def create_brain(config: dict, api_key: str | None = None) -> Brain:
    """Create a Brain instance from config dict."""
    llm = config.get("llm", {})
    provider = llm.get("provider", "anthropic")
    model = llm.get("model", "claude-haiku-4-5-20251001")

    if provider == "ollama":
        url = llm.get("url", "http://localhost:11434")
        log.info("Using Ollama: %s @ %s", model, url)
        return OllamaBrain(model=model, url=url)
    else:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        log.info("Using Anthropic: %s", model)
        return AnthropicBrain(api_key=api_key, model=model)
