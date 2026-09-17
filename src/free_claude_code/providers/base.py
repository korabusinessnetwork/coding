"""Base provider interface - extend this to implement your own provider."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass

from free_claude_code.application.model_metadata import ProviderModelInfo
from free_claude_code.core.anthropic.models import MessagesRequest
from free_claude_code.core.openai_responses import OpenAIResponsesRequest
from free_claude_code.core.reasoning import DEFAULT_REASONING_POLICY, ReasoningPolicy


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Resolved immutable configuration for one provider instance.

    Base fields apply to all providers. Provider-specific parameters
    (e.g. NIM temperature, top_p) are passed by the provider constructor.
    Now supports multiple API keys and endpoints for failover rotation.
    """

    api_keys: tuple[str, ...]
    base_urls: tuple[str, ...]
    rate_limit: int
    rate_window: int
    max_concurrency: int
    http_read_timeout: float
    http_write_timeout: float
    http_connect_timeout: float
    proxy: str | None
    log_raw_sse_events: bool
    log_api_error_tracebacks: bool

    @property
    def api_key(self) -> str | None:
        """Backward compatibility with single key access."""
        return self.api_keys[0] if self.api_keys else None

    @property
    def base_url(self) -> str:
        """Backward compatibility with single URL access."""
        return self.base_urls[0]


class BaseProvider(ABC):
    """Base class for all providers. Extend this to add your own.

    Now supports automatic rotation between multiple API keys and endpoints.
    """

    def __init__(self, config: ProviderConfig):
        self._config = config
        self._current_key_index = 0
        self._current_url_index = 0
        self._last_failure_time = 0.0
        self._failure_count = 0

    def rotate_key(self) -> None:
        """Rotate to the next API key."""
        self._current_key_index = (self._current_key_index + 1) % len(
            self._config.api_keys
        )

    def rotate_url(self) -> None:
        """Rotate to the next base URL."""
        self._current_url_index = (self._current_url_index + 1) % len(
            self._config.base_urls
        )

    def get_current_key(self) -> str | None:
        """Get the currently active API key."""
        if not self._config.api_keys:
            return None
        return self._config.api_keys[self._current_key_index]

    def get_current_url(self) -> str:
        """Get the currently active base URL."""
        return self._config.base_urls[self._current_url_index]

    @abstractmethod
    async def cleanup(self) -> None:
        """Release any resources held by this provider."""

    @abstractmethod
    async def list_model_infos(self) -> frozenset[ProviderModelInfo]:
        """Return the model metadata currently advertised by this provider."""

    @abstractmethod
    def stream_messages(
        self,
        request: MessagesRequest,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        response_model: str | None = None,
        reasoning: ReasoningPolicy = DEFAULT_REASONING_POLICY,
        request_headers: Mapping[str, str] | None = None,
        model_info: ProviderModelInfo | None = None,
    ) -> AsyncIterator[str]:
        """Validate the request before yielding a response in Anthropic SSE format."""

    @abstractmethod
    def stream_responses(
        self,
        request: OpenAIResponsesRequest,
        input_tokens: int = 0,
        *,
        request_id: str | None = None,
        response_model: str | None = None,
        reasoning: ReasoningPolicy = DEFAULT_REASONING_POLICY,
        request_headers: Mapping[str, str] | None = None,
    ) -> AsyncIterator[str]:
        """Validate the request before yielding OpenAI Responses SSE events."""
