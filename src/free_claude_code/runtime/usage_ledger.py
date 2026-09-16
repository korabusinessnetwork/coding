"""In-memory token usage and hypothetical paid-cost estimates."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from free_claude_code.core.token_estimation import estimate_text_tokens


@dataclass(frozen=True, slots=True)
class UsageEntry:
    model: str
    api: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    captured_at: str


# Reference OpenRouter paid rates in USD per million tokens. These are estimates,
# not charges, and fall back to a conservative generic paid-model rate.
_PAID_RATES: tuple[tuple[str, tuple[float, float]], ...] = (
    ("nvidia/nemotron-3-super", (0.08, 0.45)),
    ("poolside/laguna-s-2.1", (0.09, 0.18)),
    ("nex-agi/nex-n2.5-pro", (0.10, 0.40)),
    ("google/gemma-4-31b-it", (0.09, 0.34)),
)
_DEFAULT_RATE = (0.15, 0.60)


class UsageLedger:
    """Keep a bounded, process-local usage history for the Admin dashboard."""

    def __init__(self, *, max_entries: int = 2000) -> None:
        self._entries: list[UsageEntry] = []
        self._max_entries = max_entries
        self._lock = Lock()

    def record(
        self,
        *,
        model: str,
        api: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        input_tokens = max(0, input_tokens)
        output_tokens = max(0, output_tokens)
        input_rate, output_rate = _paid_rate(model)
        cost_usd = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
        entry = UsageEntry(
            model=model,
            api=api,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            captured_at=datetime.now(UTC).isoformat(),
        )
        with self._lock:
            self._entries.append(entry)
            del self._entries[:-self._max_entries]

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            entries = tuple(self._entries)
        by_model: dict[str, dict[str, object]] = defaultdict(
            lambda: {
                "input_tokens": 0,
                "output_tokens": 0,
                "requests": 0,
                "estimated_cost_usd": 0.0,
            }
        )
        for entry in entries:
            row = by_model[entry.model]
            row["input_tokens"] = int(row["input_tokens"]) + entry.input_tokens
            row["output_tokens"] = int(row["output_tokens"]) + entry.output_tokens
            row["requests"] = int(row["requests"]) + 1
            row["estimated_cost_usd"] = float(row["estimated_cost_usd"]) + entry.cost_usd
        total_input = sum(entry.input_tokens for entry in entries)
        total_output = sum(entry.output_tokens for entry in entries)
        total_cost = sum(entry.cost_usd for entry in entries)
        return {
            "requests": len(entries),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "estimated_cost_usd": round(total_cost, 6),
            "models": [
                {"model": model, **values}
                for model, values in sorted(by_model.items())
            ],
            "pricing_basis": "Hypothetical OpenRouter paid rates; free requests are not billed.",
        }


def _paid_rate(model: str) -> tuple[float, float]:
    normalized = model.removeprefix("free-claude-code/")
    normalized = normalized.removeprefix("open_router/")
    for prefix, rates in _PAID_RATES:
        if normalized.startswith(prefix):
            return rates
    return _DEFAULT_RATE


def estimate_output_tokens(text: str) -> int:
    """Estimate visible output tokens from a response fragment."""

    return estimate_text_tokens(text) if text else 0
