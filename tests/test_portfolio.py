from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from monthly_limit_order_review.portfolio import analyze_portfolio


def test_bucket_allocations_are_computed(sample_snapshot, portfolio_policy_config) -> None:
    analysis = analyze_portfolio(sample_snapshot, portfolio_policy_config)
    allocations = {item.bucket: item for item in analysis["bucket_allocations"]}

    assert allocations["core"].actual_pct == Decimal("0.3600")
    assert allocations["jun_core"].actual_pct == Decimal("0.1600")
    assert allocations["satellite_core"].actual_pct == Decimal("0.1600")


def test_semiconductor_exposure_is_aggregated(sample_snapshot, portfolio_policy_config) -> None:
    analysis = analyze_portfolio(sample_snapshot, portfolio_policy_config)

    assert analysis["semi_exposure_pct"] == Decimal("0.1600")


def test_sox_named_funds_are_treated_as_satellite_core(sample_snapshot, portfolio_policy_config) -> None:
    sox_like_holdings = list(sample_snapshot.holdings)
    sox_like_holdings[2] = replace(
        sox_like_holdings[2],
        symbol="NISSEI_SOX_1",
        name="ニッセイSOX指数インデックスファンド〈米国半導体株〉",
        asset_class="jun_core",
    )
    sox_like_snapshot = replace(sample_snapshot, holdings=sox_like_holdings)

    analysis = analyze_portfolio(sox_like_snapshot, portfolio_policy_config)
    allocations = {item.bucket: item for item in analysis["bucket_allocations"]}

    assert allocations["satellite_core"].actual_pct == Decimal("0.3200")
    assert analysis["semi_exposure_pct"] == Decimal("0.3200")


def test_pltr_ratio_warning_is_emitted(sample_snapshot, portfolio_policy_config) -> None:
    analysis = analyze_portfolio(sample_snapshot, portfolio_policy_config)

    assert any(warning.code == "pltr_limit" for warning in analysis["warnings"])


def test_cash_warning_is_emitted_for_low_liquidity(sample_snapshot, portfolio_policy_config) -> None:
    low_cash_holdings = list(sample_snapshot.holdings)
    low_cash_holdings[0] = replace(low_cash_holdings[0], market_value_jpy=Decimal("200000"))
    low_cash_holdings[1] = replace(low_cash_holdings[1], market_value_jpy=Decimal("2800000"))
    low_cash_snapshot = replace(sample_snapshot, holdings=low_cash_holdings)

    analysis = analyze_portfolio(low_cash_snapshot, portfolio_policy_config)

    warning_codes = {warning.code for warning in analysis["warnings"]}
    assert "liquidity_floor" in warning_codes
    assert "cash_below_preferred" in warning_codes
