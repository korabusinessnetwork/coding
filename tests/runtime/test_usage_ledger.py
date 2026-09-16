from free_claude_code.runtime.usage_ledger import UsageLedger


def test_usage_ledger_estimates_paid_cost_for_opencode_model_ids() -> None:
    ledger = UsageLedger()
    ledger.record(
        model="free-claude-code/open_router/nvidia/nemotron-3-super-120b-a12b:free",
        api="responses",
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )

    snapshot = ledger.snapshot()

    assert snapshot["requests"] == 1
    assert snapshot["total_tokens"] == 2_000_000
    assert snapshot["estimated_cost_usd"] == 0.53
    assert snapshot["pricing_basis"]


def test_usage_ledger_groups_models_and_keeps_free_requests_unbilled() -> None:
    ledger = UsageLedger()
    ledger.record(
        model="open_router/google/gemma-4-31b-it:free",
        api="messages",
        input_tokens=100,
        output_tokens=50,
    )
    ledger.record(
        model="open_router/google/gemma-4-31b-it:free",
        api="messages",
        input_tokens=200,
        output_tokens=100,
    )

    snapshot = ledger.snapshot()

    assert snapshot["requests"] == 2
    assert snapshot["input_tokens"] == 300
    assert snapshot["output_tokens"] == 150
    assert len(snapshot["models"]) == 1
    assert snapshot["models"][0]["requests"] == 2
