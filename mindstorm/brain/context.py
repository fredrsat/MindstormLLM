"""Conversation context management for the LLM brain."""
from __future__ import annotations


class Context:
    """Rolling context window for LLM conversation."""

    def __init__(self, max_pairs: int = 15):
        self.max_pairs = max_pairs
        self._messages: list[dict] = []

    def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})
        self._trim()

    def add_assistant_message(self, content: str) -> None:
        self._messages.append({"role": "assistant", "content": content})
        self._trim()

    def get_messages(self) -> list[dict]:
        return list(self._messages)

    def _trim(self) -> None:
        """Keep only the last N message pairs."""
        max_messages = self.max_pairs * 2
        if len(self._messages) > max_messages:
            self._messages = self._messages[-max_messages:]

    def remove_last(self) -> None:
        """Remove the last message (e.g. on LLM failure)."""
        if self._messages:
            self._messages.pop()

    def clear(self) -> None:
        self._messages.clear()
