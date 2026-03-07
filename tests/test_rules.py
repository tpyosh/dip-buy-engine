from __future__ import annotations

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


def test_pltr_shallow_tranche_is_suppressed(sample_candidate_orders) -> None:
    pltr_first = next(candidate for candidate in sample_candidate_orders if candidate.symbol == "PLTR")

    assert pltr_first.suppressed is True
    assert any("PLTR already exceeds policy cap" in reason for reason in pltr_first.suppression_reasons)


def test_sox_buy_signal_uses_recent_high(buy_rules_config, sample_market_references) -> None:
    signal = calculate_sox_buy_signal(buy_rules_config, sample_market_references)

    assert signal["drawdown_pct"] == Decimal("-8.00")
    assert signal["within_buy_zone"] is True

