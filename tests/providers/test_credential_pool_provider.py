import json

import httpx2
import pytest
from openai import AsyncOpenAI

from free_claude_code.core.anthropic import ReasoningReplayMode
from free_claude_code.core.anthropic.models import MessagesRequest
from free_claude_code.providers.openai_chat import (
    NO_REASONING,
    OpenAIChatProfile,
    OpenAIChatProvider,
    OpenAIChatRequestPolicy,
)
from tests.providers.support import immediate_admission, make_provider_config


@pytest.mark.asyncio
async def test_provider_retries_next_pool_key_after_uncommitted_rate_limit() -> None:
    keys: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        keys.append(request.headers["Authorization"])
        if len(keys) == 1:
            return httpx2.Response(429, json={"error": {"message": "limited"}})
        event = {
            "id": "chat",
            "object": "chat.completion.chunk",
            "created": 0,
            "model": "upstream",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "ok"},
                    "finish_reason": "stop",
                }
            ],
        }
        return httpx2.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n",
        )

    pool = httpx2.MockTransport(handler)
    client = AsyncOpenAI(
        api_key="unused",
        base_url="https://provider.invalid/v1",
        http_client=httpx2.AsyncClient(transport=pool),
        max_retries=0,
    )
    provider = OpenAIChatProvider(
        make_provider_config("key-a,key-b", "https://provider.invalid/v1"),
        profile=OpenAIChatProfile(
            OpenAIChatRequestPolicy("TEST", ReasoningReplayMode.DISABLED),
            NO_REASONING,
        ),
        admission=immediate_admission(max_attempts=3),
        client=client,
        endpoint_transport=pool,
    )
    try:
        request = MessagesRequest(
            model="upstream", messages=[{"role": "user", "content": "hi"}]
        )
        assert [event async for event in provider.stream_messages(request)]
    finally:
        await provider.cleanup()
        await client.close()

    assert keys == ["Bearer key-a", "Bearer key-b"]
