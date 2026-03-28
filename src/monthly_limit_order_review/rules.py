from __future__ import annotations

from decimal import Decimal

from .candidate_metrics import compute_candidate_metrics
from .portfolio_metrics import compute_portfolio_metrics
from .utils import quantize, to_decimal
from .validation import apply_candidate_validations


def calculate_candidate_orders(
    snapshot,
    buy_rules_config: dict,
    portfolio_policy: dict,
    market_references: list,
    *,
    liquidity_jpy=None,
    symbol_weights=None,
):
    portfolio_metrics = compute_portfolio_metrics(snapshot, portfolio_policy)
    candidates = compute_candidate_metrics(
        snapshot,
        buy_rules_config,
        portfolio_policy,
        market_references,
        portfolio_metrics["resolved_buckets"],
        portfolio_metrics["bucket_allocations"],
    )
    validated_candidates, _ = apply_candidate_validations(candidates, buy_rules_config)
    return validated_candidates


def calculate_sox_buy_signal(
    buy_rules_config: dict,
    market_references: list,
    *,
    bucket_allocations: list | None = None,
    exposure_breakdown: dict | None = None,
) -> dict:
    reference_map = {reference.symbol: reference for reference in market_references}
    sox_config = buy_rules_config.get("sox_buy_judgement", {})
    proxy_symbol = sox_config.get("proxy_symbol")
    if proxy_symbol not in reference_map:
        raise ValueError(f"Missing market reference for SOX proxy {proxy_symbol}")

    proxy_reference = reference_map[proxy_symbol]
    current_price = to_decimal(proxy_reference.current_price, field_name=f"{proxy_symbol}.current_price")
    recent_high_21d = to_decimal(proxy_reference.recent_high_21d, field_name=f"{proxy_symbol}.recent_high_21d")
    recent_high_63d = to_decimal(proxy_reference.recent_high_63d, field_name=f"{proxy_symbol}.recent_high_63d")
    drawdown_21d = quantize(((current_price - recent_high_21d) / recent_high_21d) * Decimal("100"), 2)
    drawdown_63d = quantize(((current_price - recent_high_63d) / recent_high_63d) * Decimal("100"), 2)

    buy_zone_min = to_decimal(sox_config["buy_zone_min_pct"], field_name="sox_buy_judgement.buy_zone_min_pct")
    buy_zone_max = to_decimal(sox_config["buy_zone_max_pct"], field_name="sox_buy_judgement.buy_zone_max_pct")
    near_boundary_threshold = to_decimal(
        sox_config.get("near_boundary_threshold_pct", 1),
        field_name="sox_buy_judgement.near_boundary_threshold_pct",
    )
    within_buy_zone = buy_zone_min <= drawdown_63d <= buy_zone_max
    near_boundary = (
        abs(drawdown_63d - buy_zone_min) <= near_boundary_threshold
        or abs(drawdown_63d - buy_zone_max) <= near_boundary_threshold
    )

    allocation_map = {allocation.bucket: allocation for allocation in (bucket_allocations or [])}
    related_bucket = allocation_map.get("satellite_core")
    priority_lowered = False
    priority_lowered_reason = None
    if bool(sox_config.get("deprioritize_when_related_bucket_over_target", False)) and related_bucket is not None:
        if related_bucket.target_pct is not None and related_bucket.actual_pct > related_bucket.target_pct:
            priority_lowered = True
            priority_lowered_reason = sox_config.get("priority_lowered_note", "related_bucket_over_target")
    return {
        "proxy_symbol": proxy_symbol,
        "current_price": current_price,
        "recent_high_21d": recent_high_21d,
        "recent_high_63d": recent_high_63d,
        "drawdown_pct": drawdown_63d,
        "drawdown_pct_from_21d_high": drawdown_21d,
        "drawdown_pct_from_63d_high": drawdown_63d,
        "buy_zone": f"{buy_zone_min}% to {buy_zone_max}%",
        "buy_zone_rule_text": f"drawdown from 63d high between {buy_zone_min}% and {buy_zone_max}%",
        "within_buy_zone": within_buy_zone,
        "within_buy_zone_boolean": within_buy_zone,
        "near_boundary_boolean": near_boundary,
        "monthly_buy_budget_jpy": sox_config.get("monthly_buy_budget_jpy", {}),
        "related_bucket_actual_pct": related_bucket.actual_pct if related_bucket is not None else None,
        "related_bucket_target_pct": related_bucket.target_pct if related_bucket is not None else None,
        "semiconductor_exposure_total_pct": (
            exposure_breakdown.get("semiconductor_exposure_total_pct") if exposure_breakdown else None
        ),
        "priority_lowered_boolean": priority_lowered,
        "priority_lowered_reason": priority_lowered_reason,
    }
