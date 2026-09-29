"""DeepSeek provider: request contract for the OpenAI-compatible endpoint."""

import json

import pytest

from jsint_core.core.llm import MessageRole, create_llm_provider
from jsint_core.core.llm.providers.deepseek import DeepSeekProvider
from jsint_core.core.llm.types import ChatMessage

ENDPOINT = "https://api.deepseek.com/chat/completions"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Keep ambient LLM settings from leaking into the assertions."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)


def test_factory_requires_the_api_key(monkeypatch):
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        create_llm_provider(provider="deepseek")


def test_factory_reads_the_api_key_from_the_environment(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")

    assert isinstance(create_llm_provider(provider="deepseek"), DeepSeekProvider)


@pytest.mark.asyncio
async def test_complete_posts_openai_compatible_payload(httpx_mock):
    httpx_mock.add_response(
        url=ENDPOINT, json={"choices": [{"message": {"content": "pong"}}]}
    )
    provider = create_llm_provider(provider="deepseek", api_key="test-key")

    answer = await provider.complete(
        [ChatMessage(role=MessageRole.USER, content="ping")]
    )

    assert answer == "pong"
    request = httpx_mock.get_request()
    assert request.headers["authorization"] == "Bearer test-key"
    assert json.loads(request.content) == {
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": "ping"}],
        "stream": False,
    }


@pytest.mark.asyncio
async def test_stream_yields_content_deltas_and_ignores_keepalives(httpx_mock):
    httpx_mock.add_response(
        url=ENDPOINT,
        text=(
            'data: {"choices":[{"delta":{"content":"po"}}]}\n\n'
            'data: {"choices":[]}\n\n'
            'data: {"choices":[{"delta":{"content":"ng"}}]}\n\n'
            "data: [DONE]\n\n"
        ),
    )
    provider = create_llm_provider(provider="deepseek", api_key="test-key")

    chunks = [
        chunk
        async for chunk in provider.stream(
            [ChatMessage(role=MessageRole.USER, content="ping")]
        )
    ]

    assert chunks == ["po", "ng"]
    assert json.loads(httpx_mock.get_request().content)["stream"] is True
