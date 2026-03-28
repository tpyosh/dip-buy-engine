from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from monthly_limit_order_review.portfolio import analyze_portfolio
from monthly_limit_order_review.portfolio_metrics import build_core_buy_materials


def test_bucket_allocations_are_computed(sample_snapshot, portfolio_policy_config) -> None:
    analysis = analyze_portfolio(sample_snapshot, portfolio_policy_config)
    allocations = {item.bucket: item for item in analysis["bucket_allocations"]}

    assert allocations["core"].actual_pct == Decimal("0.3600")
    assert allocations["jun_core"].actual_pct == Decimal("0.1600")
    assert allocations["satellite_core"].actual_pct == Decimal("0.1600")


def test_semiconductor_exposure_is_aggregated(sample_snapshot, portfolio_policy_config) -> None:
    analysis = analyze_portfolio(sample_snapshot, portfolio_policy_config)

    assert analysis["semi_exposure_pct"] == Decimal("0.1600")
    assert analysis["exposure_breakdown"]["semiconductor_exposure_total_jpy"] == Decimal("800000")


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

    warning_by_code = {warning.code: warning for warning in analysis["warnings"]}
    assert warning_by_code["liquidity_floor"].severity == "error"
    assert "cash_below_preferred" in warning_by_code


def test_core_budget_stays_standard_without_large_dual_imbalance(
    sample_snapshot,
    sample_portfolio_analysis,
    sample_market_references,
    buy_rules_config,
) -> None:
    core_buy_materials, _ = build_core_buy_materials(
        sample_snapshot,
        sample_portfolio_analysis["bucket_allocations"],
        sample_portfolio_analysis["resolved_buckets"],
        sample_market_references,
        buy_rules_config,
    )

    assert core_buy_materials["monthly_core_budget_tier"] == "standard"
    assert core_buy_materials["recommended_monthly_core_buy_budget_jpy"] == 100000
    assert core_buy_materials["monthly_core_budget_override_active"] is False


def test_core_budget_shifts_to_upper_tier_when_core_low_and_cash_high(
    sample_snapshot,
    portfolio_policy_config,
    sample_market_references,
    buy_rules_config,
) -> None:
    rebalanced_holdings = list(sample_snapshot.holdings)
    rebalanced_holdings[0] = replace(rebalanced_holdings[0], market_value_jpy=Decimal("2400000"))
    rebalanced_holdings[1] = replace(rebalanced_holdings[1], market_value_jpy=Decimal("600000"))
    stressed_snapshot = replace(sample_snapshot, holdings=rebalanced_holdings)
    stressed_analysis = analyze_portfolio(stressed_snapshot, portfolio_policy_config)
    core_buy_materials, _ = build_core_buy_materials(
        stressed_snapshot,
        stressed_analysis["bucket_allocations"],
        stressed_analysis["resolved_buckets"],
        sample_market_references,
        buy_rules_config,
    )

    assert core_buy_materials["monthly_core_budget_tier"] == "aggressive"
    assert core_buy_materials["recommended_monthly_core_buy_budget_jpy"] == 300000
    assert core_buy_materials["monthly_core_budget_override_active"] is True
    assert core_buy_materials["monthly_core_budget_override_reason"] == "core_underweight_and_cash_overweight"
