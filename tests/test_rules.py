from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from monthly_limit_order_review.rules import calculate_sox_buy_signal


def test_candidate_prices_follow_rules(sample_candidate_orders) -> None:
    grouped = {}
    for candidate in sample_candidate_orders:
        grouped.setdefault(candidate.symbol, []).append(candidate)

    assert grouped["CIBR"][0].limit_price == Decimal("95.00")
    assert grouped["URA"][0].limit_price == Decimal("94.00")
    assert grouped["MSFT"][0].limit_price == Decimal("470.00")
    assert len(sample_candidate_orders) == 12


def test_candidate_avg20_gap_pct_is_precomputed(sample_candidate_orders) -> None:
    first_msft = next(candidate for candidate in sample_candidate_orders if candidate.symbol == "MSFT")

    assert first_msft.avg20_base_price == Decimal("500")
    assert first_msft.avg20_gap_pct == Decimal("-6.00")


def test_pltr_shallow_tranche_is_suppressed(sample_candidate_orders) -> None:
    pltr_first = next(candidate for candidate in sample_candidate_orders if candidate.symbol == "PLTR")

    assert pltr_first.suppressed is True
    assert pltr_first.suppressed_reason_code == "limit_above_current"
    assert pltr_first.suppressed_reason_text == "Calculated limit price is not below the current price."
    assert "limit_above_current" in (pltr_first.note_for_chatgpt or "")


def test_sox_buy_signal_uses_recent_high(
    buy_rules_config,
    sample_market_references,
    sample_portfolio_analysis,
    sample_exposure_breakdown,
) -> None:
    signal = calculate_sox_buy_signal(
        buy_rules_config,
        sample_market_references,
        bucket_allocations=sample_portfolio_analysis["bucket_allocations"],
        exposure_breakdown=sample_exposure_breakdown,
    )

    assert signal["drawdown_pct"] == Decimal("-8.00")
    assert signal["drawdown_pct_from_21d_high"] == Decimal("-4.17")
    assert signal["within_buy_zone"] is True
    assert signal["within_buy_zone_boolean"] is True
    assert signal["near_boundary_boolean"] is False
    assert "semiconductor_direct_exposure_pct" in signal
    assert "indirect_ai_infra_exposure_pct" in signal
    assert signal["priority_lowered_boolean"] is True
    assert signal["priority_lowered_reason"] == "related_bucket_over_target"
    assert "explanation" in signal
    assert signal["explanation"]["bucket_context"]["related_bucket"] == "satellite_core"
    assert "semiconductor_direct_exposure_pct" in signal["explanation"]["exposure_context"]


def test_sox_buy_signal_is_false_when_drawdown_is_zero(
    buy_rules_config,
    sample_market_references,
    sample_portfolio_analysis,
    sample_exposure_breakdown,
) -> None:
    adjusted_references = [
        replace(reference, current_price=reference.recent_high_63d, recent_high_21d=reference.recent_high_63d)
        if reference.symbol == "SMH"
        else reference
        for reference in sample_market_references
    ]

    signal = calculate_sox_buy_signal(
        buy_rules_config,
        adjusted_references,
        bucket_allocations=sample_portfolio_analysis["bucket_allocations"],
        exposure_breakdown=sample_exposure_breakdown,
    )

    assert signal["drawdown_pct"] == Decimal("0.00")
    assert signal["within_buy_zone"] is False
    assert signal["within_buy_zone_boolean"] is False
