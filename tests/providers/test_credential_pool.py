import pytest

from free_claude_code.providers.credential_pool import CredentialPool


@pytest.mark.asyncio
async def test_credential_pool_round_robins_keys_and_urls() -> None:
    pool = CredentialPool(
        api_keys=("key-a", "key-b"),
        base_urls=("https://one.invalid/v1", "https://two.invalid/v1"),
    )

    endpoints = [await pool.endpoint() for _ in range(3)]

    assert [(item.api_key, item.base_url) for item in endpoints] == [
        ("key-a", "https://one.invalid/v1"),
        ("key-b", "https://two.invalid/v1"),
        ("key-a", "https://one.invalid/v1"),
    ]


@pytest.mark.asyncio
async def test_credential_pool_wraps_independent_key_and_url_lengths() -> None:
    pool = CredentialPool(
        api_keys=("key-a", "key-b"),
        base_urls=("https://one.invalid/v1",),
    )

    endpoints = [await pool.endpoint(force_refresh=True) for _ in range(3)]

    assert [item.api_key for item in endpoints] == ["key-a", "key-b", "key-a"]
    assert {item.base_url for item in endpoints} == {"https://one.invalid/v1"}
