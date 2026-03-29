from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from monthly_limit_order_review.candidate_metrics import compute_candidate_metrics
from monthly_limit_order_review.validation import apply_candidate_validations


def test_bucket_over_target_candidates_get_default_behavior_notes(
    sample_snapshot,
    buy_rules_config,
    portfolio_policy_config,
    sample_market_references,
    sample_portfolio_analysis,
) -> None:
    candidates = compute_candidate_metrics(
        sample_snapshot,
        buy_rules_config,
        portfolio_policy_config,
        sample_market_references,
        sample_portfolio_analysis["resolved_buckets"],
        sample_portfolio_analysis["bucket_allocations"],
    )

    cibr_first = next(candidate for candidate in candidates if candidate.symbol == "CIBR" and candidate.drawdown_pct == Decimal("-5"))
    ura_deep = next(candidate for candidate in candidates if candidate.symbol == "URA" and candidate.drawdown_pct == Decimal("-15"))

    assert "default_deep_only_due_to_bucket_over_target" in (cibr_first.note_for_chatgpt or "")
    assert "default_allow_deep_drawdown_even_if_bucket_over_target" in (ura_deep.note_for_chatgpt or "")
    assert cibr_first.suppressed is True
    assert cibr_first.suppressed_reason_code == "bucket_over_target_shallow_suppressed"


def test_high_volatility_shallow_candidate_is_policy_suppressed(
    sample_snapshot,
    buy_rules_config,
    portfolio_policy_config,
    sample_market_references,
    sample_portfolio_analysis,
) -> None:
    adjusted_references = [
        replace(reference, current_price=Decimal("200"), mean_close_20d=Decimal("150"))
        if reference.symbol == "PLTR"
        else reference
        for reference in sample_market_references
    ]
    candidates = compute_candidate_metrics(
        sample_snapshot,
        buy_rules_config,
        portfolio_policy_config,
        adjusted_references,
        sample_portfolio_analysis["resolved_buckets"],
        sample_portfolio_analysis["bucket_allocations"],
    )
    validated_candidates, warnings = apply_candidate_validations(candidates, buy_rules_config)

    pltr_first = next(candidate for candidate in validated_candidates if candidate.symbol == "PLTR" and candidate.drawdown_pct == Decimal("-10"))

    assert pltr_first.suppressed is True
    assert pltr_first.suppressed_reason_code == "high_volatility_shallow_suppressed"
    assert "rule_based_high_volatility_shallow_suppression" in (pltr_first.note_for_chatgpt or "")
    assert any(warning.code == "high_volatility_shallow_suppressed" for warning in warnings)


def test_candidate_mode_switch_boosts_core_and_jun_core(
    sample_snapshot,
    buy_rules_config,
    portfolio_policy_config,
    sample_market_references,
    sample_portfolio_analysis,
) -> None:
    candidates = compute_candidate_metrics(
        sample_snapshot,
        buy_rules_config,
        portfolio_policy_config,
        sample_market_references,
        sample_portfolio_analysis["resolved_buckets"],
        sample_portfolio_analysis["bucket_allocations"],
        mode_context={"portfolio_management_mode": "rebalance"},
    )
    msft = next(candidate for candidate in candidates if candidate.symbol == "MSFT" and candidate.drawdown_pct == Decimal("-10"))
    cibr = next(candidate for candidate in candidates if candidate.symbol == "CIBR" and candidate.drawdown_pct == Decimal("-8"))

    assert "mode_rebalance_priority_boost" in (msft.note_for_chatgpt or "")
    assert "mode_rebalance_relative_deprioritization" in (cibr.note_for_chatgpt or "")
    assert msft.explanation["mode_context"]["active_mode"] == "rebalance"
    assert "rule_based_reason" in msft.explanation
    assert msft.reference_method == "mean_close_30d"
