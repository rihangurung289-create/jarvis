"""Conversational AI — understand questions and reply naturally."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import config


class AIResponder:
    """Generates natural-language replies using an LLM (OpenAI or local Ollama)."""

    def __init__(self) -> None:
        self._history: list[dict[str, str]] = []

    @property
    def enabled(self) -> bool:
        if not config.ENABLE_AI_CHAT:
            return False
        if config.AI_PROVIDER == "openai":
            return self._is_valid_openai_key(self._openai_api_key())
        if config.AI_PROVIDER == "ollama":
            return True
        return False

    def generate(self, user_text: str, user_name: str = "there") -> str:
        text = user_text.strip()
        if not text:
            return "I didn't catch that. Could you say it again?"

        if not config.ENABLE_AI_CHAT:
            return _static_fallback()

        if not self.enabled:
            return (
                "AI chat needs an OpenAI API key. "
                "Copy .env.example to .env and add OPENAI_API_KEY, then restart Jarvis."
            )

        try:
            reply = self._call_llm(text, user_name)
            self._remember_turn(text, reply)
            return reply
        except urllib.error.HTTPError as exc:
            return _openai_http_error(exc)
        except urllib.error.URLError as exc:
            if config.AI_PROVIDER == "ollama":
                return (
                    "I couldn't reach Ollama. Make sure it's running "
                    f"({config.OLLAMA_BASE_URL}) and the model "
                    f'"{config.OLLAMA_MODEL}" is installed.'
                )
            return f"Sorry, I couldn't reach OpenAI. Check your internet connection. ({exc.reason})"
        except (KeyError, json.JSONDecodeError, IndexError) as exc:
            return f"Sorry, I got an unexpected response from the AI. ({exc})"

    def clear_history(self) -> None:
        self._history.clear()

    def _openai_api_key(self) -> str:
        return (
            os.environ.get("OPENAI_API_KEY", "").strip()
            or config.OPENAI_API_KEY.strip()
        )

    @staticmethod
    def _is_valid_openai_key(key: str) -> bool:
        if not key or key.startswith("sk-your-key"):
            return False
        return key.startswith("sk-")

    def _remember_turn(self, user_text: str, reply: str) -> None:
        self._history.append({"role": "user", "content": user_text})
        self._history.append({"role": "assistant", "content": reply})
        max_messages = config.AI_MAX_HISTORY_TURNS * 2
        if len(self._history) > max_messages:
            self._history = self._history[-max_messages:]

    def _system_prompt(self, user_name: str) -> str:
        return config.AI_SYSTEM_PROMPT.format(
            user_name=user_name,
            wake_word=config.WAKE_WORD,
            max_words=config.AI_MAX_RESPONSE_WORDS,
        )

    def _messages(self, user_text: str, user_name: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._system_prompt(user_name)},
            *self._history,
            {"role": "user", "content": user_text},
        ]

    def _call_llm(self, user_text: str, user_name: str) -> str:
        if config.AI_PROVIDER == "ollama":
            return self._call_ollama(user_text, user_name)
        return self._call_openai(user_text, user_name)

    def _call_openai(self, user_text: str, user_name: str) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        body = {
            "model": config.OPENAI_MODEL,
            "messages": self._messages(user_text, user_name),
            "max_tokens": 180,
            "temperature": 0.7,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._openai_api_key()}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=config.AI_REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()

    def _call_ollama(self, user_text: str, user_name: str) -> str:
        base = config.OLLAMA_BASE_URL.rstrip("/")
        url = f"{base}/api/chat"
        body = {
            "model": config.OLLAMA_MODEL,
            "messages": self._messages(user_text, user_name),
            "stream": False,
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=config.AI_REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["message"]["content"].strip()


_responder: AIResponder | None = None


def get_responder() -> AIResponder:
    global _responder
    if _responder is None:
        _responder = AIResponder()
    return _responder


def generate_reply(user_text: str, user_name: str = "there") -> str:
    """Return a natural spoken reply for the user's question or message."""
    return get_responder().generate(user_text, user_name)


def _static_fallback() -> str:
    return (
        "I didn't understand that. Try: open notepad, volume up, "
        "set volume to fifty, or ask me a question."
    )


def _openai_http_error(exc: urllib.error.HTTPError) -> str:
    if exc.code == 401:
        return "Your OpenAI API key is invalid. Check OPENAI_API_KEY in your .env file."
    if exc.code == 429:
        return "OpenAI rate limit reached. Wait a moment and try again."
    if exc.code == 402:
        return "Your OpenAI account needs billing set up. Visit platform.openai.com."
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        message = payload.get("error", {}).get("message", "")
        if message:
            return f"OpenAI error: {message}"
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return f"OpenAI request failed with status {exc.code}."
