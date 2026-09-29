"""DeepSeek chat provider.

DeepSeek exposes an OpenAI-compatible REST API (https://api-docs.deepseek.com/),
so this provider talks to it over httpx rather than pulling in the OpenAI SDK,
which is not part of this workspace's dependency set.
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from ..types import ChatMessage

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-flash"

# A streaming response can idle while the model is thinking, so the read timeout
# is generous while connect/write stay tight.
_TIMEOUT = httpx.Timeout(30.0, read=300.0)


class DeepSeekProvider:
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
    ):
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def _endpoint(self) -> str:
        return f"{self._base_url}/chat/completions"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, messages: List[ChatMessage], stream: bool) -> Dict[str, Any]:
        return {
            "model": self._model,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            "stream": stream,
        }

    @staticmethod
    def _delta_content(chunk: Dict[str, Any]) -> Optional[str]:
        choices = chunk.get("choices") or []
        if not choices:
            return None
        delta = choices[0].get("delta") or {}
        return delta.get("content")

    async def stream(self, messages: List[ChatMessage]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            async with client.stream(
                "POST",
                self._endpoint,
                headers=self._headers,
                json=self._payload(messages, stream=True),
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if not data or data == "[DONE]":
                        continue
                    content = self._delta_content(json.loads(data))
                    if content:
                        yield content

    async def complete(self, messages: List[ChatMessage]) -> str:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                self._endpoint,
                headers=self._headers,
                json=self._payload(messages, stream=False),
            )
            response.raise_for_status()
            body = response.json()

        choices = body.get("choices") or []
        if not choices:
            raise ValueError("DeepSeek returned no choices")
        return choices[0].get("message", {}).get("content") or ""
