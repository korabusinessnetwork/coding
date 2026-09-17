"""Request-scoped round-robin endpoints for authorized credential pools."""

import asyncio

from free_claude_code.providers.endpoint_types import HttpEndpoint


class CredentialPool:
    """Select configured credentials in round-robin order.

    The pool is deliberately limited to a provider's configured credentials.
    It does not create accounts, alter quotas, or retry authentication failures.
    """

    def __init__(
        self, *, api_keys: tuple[str, ...], base_urls: tuple[str, ...]
    ) -> None:
        if not api_keys or not base_urls:
            raise ValueError("Credential pools require at least one key and base URL")
        self._api_keys = api_keys
        self._base_urls = base_urls
        self._next_index = 0
        self._lock = asyncio.Lock()

    async def endpoint(self, *, force_refresh: bool = False) -> HttpEndpoint:
        """Return the next endpoint; retries request a new pool member."""
        del force_refresh
        async with self._lock:
            index = self._next_index
            self._next_index = (index + 1) % max(
                len(self._api_keys), len(self._base_urls)
            )
        return HttpEndpoint(
            base_url=self._base_urls[index % len(self._base_urls)],
            headers={},
            api_key=self._api_keys[index % len(self._api_keys)],
        )
