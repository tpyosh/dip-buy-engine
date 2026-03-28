from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .exposure_metrics import build_exposure_breakdown, get_exposure_group, holding_matches_exposure_group
from .models import BucketAllocation, Holding, MarketReference, PortfolioSnapshot, PortfolioWarning
from .utils import percent, quantize, to_optional_decimal


def compute_portfolio_metrics(snapshot: PortfolioSnapshot, policy_config: dict) -> dict:
    bucket_values: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    symbol_weights: dict[str, Decimal] = {}
    resolved_buckets: dict[str, str] = {}

    for holding in snapshot.holdings:
        bucket = resolve_bucket(holding, policy_config)
        resolved_buckets[holding.symbol] = bucket
        bucket_values[bucket] += holding.market_value_jpy
        symbol_weights[holding.symbol] = percent(holding.market_value_jpy, snapshot.total_assets_jpy)

    bucket_allocations = compute_bucket_allocations(snapshot, policy_config, bucket_values)
    exposure_breakdown = build_exposure_breakdown(snapshot, policy_config, resolved_buckets)
    warnings = compute_bucket_warnings(
        snapshot=snapshot,
        policy_config=policy_config,
        bucket_values=bucket_values,
        symbol_weights=symbol_weights,
        bucket_allocations=bucket_allocations,
        resolved_buckets=resolved_buckets,
    )

    return {
        "bucket_allocations": bucket_allocations,
        "bucket_values": dict(bucket_values),
        "warnings": warnings,
        "liquidity_jpy": bucket_values.get("liquidity", Decimal("0")),
        "resolved_buckets": resolved_buckets,
        "symbol_weights": symbol_weights,
        "semi_exposure_pct": exposure_breakdown["semiconductor_exposure_total_pct"],
        "semi_exposure_jpy": exposure_breakdown["semiconductor_exposure_total_jpy"],
        "exposure_breakdown": exposure_breakdown,
        "portfolio_summary": build_portfolio_summary(snapshot, bucket_allocations, policy_config),
    }


def resolve_bucket(holding: Holding, policy_config: dict) -> str:
    explicit_bucket = policy_config.get("symbol_to_bucket", {}).get(holding.symbol)
    if explicit_bucket is not None:
        return explicit_bucket

    if holding_matches_exposure_group(holding, get_exposure_group(policy_config, "semiconductor")):
        return "satellite_core"
    return holding.asset_class


def compute_bucket_allocations(
    snapshot: PortfolioSnapshot,
    policy_config: dict,
    bucket_values: dict[str, Decimal],
) -> list[BucketAllocation]:
    allocations: list[BucketAllocation] = []
    bucket_policies = policy_config.get("portfolio_buckets", {})
    all_buckets = sorted(set(bucket_values) | set(bucket_policies))
    for bucket in all_buckets:
        value = bucket_values.get(bucket, Decimal("0"))
        bucket_policy = bucket_policies.get(bucket, {})
        target_pct = to_optional_decimal(bucket_policy.get("target_pct"))
        preferred_range = bucket_policy.get("preferred_pct_range") or [None, None]
        preferred_min = to_optional_decimal(preferred_range[0]) if preferred_range[0] is not None else None
        preferred_max = to_optional_decimal(preferred_range[1]) if preferred_range[1] is not None else None
        actual_pct = percent(value, snapshot.total_assets_jpy)
        delta_pct = quantize(actual_pct - target_pct, 4) if target_pct is not None else None
        allocations.append(
            BucketAllocation(
                bucket=bucket,
                market_value_jpy=value,
                actual_pct=actual_pct,
                target_pct=target_pct,
                delta_pct=delta_pct,
                preferred_min_pct=preferred_min,
                preferred_max_pct=preferred_max,
            )
        )
    return allocations


def build_bucket_allocation_table(bucket_allocations: list[BucketAllocation]) -> list[dict]:
    return [
        {
            "bucket": allocation.bucket,
            "market_value_jpy": allocation.market_value_jpy,
            "actual_pct": allocation.actual_pct,
            "target_pct": allocation.target_pct,
            "delta_pct": allocation.delta_pct,
        }
        for allocation in bucket_allocations
    ]


def build_portfolio_summary(
    snapshot: PortfolioSnapshot,
    bucket_allocations: list[BucketAllocation],
    policy_config: dict,
) -> dict:
    allocations = {allocation.bucket: allocation for allocation in bucket_allocations}
    core = allocations.get("core")
    liquidity = allocations.get("liquidity")
    liquidity_target_pct = liquidity.target_pct if liquidity is not None else None
    liquidity_actual_pct = liquidity.actual_pct if liquidity is not None else None
    cash_excess_pct = None
    if liquidity_actual_pct is not None and liquidity_target_pct is not None:
        cash_excess_pct = quantize(liquidity_actual_pct - liquidity_target_pct, 4)

    return {
        "core_actual_pct": core.actual_pct if core is not None else None,
        "core_target_pct": core.target_pct if core is not None else None,
        "core_delta_pct": core.delta_pct if core is not None else None,
        "liquidity_actual_pct": liquidity_actual_pct,
        "liquidity_target_pct": liquidity_target_pct,
        "cash_excess_pct": cash_excess_pct,
        "core_bucket_total_jpy": core.market_value_jpy if core is not None else Decimal("0"),
        "total_assets_jpy": snapshot.total_assets_jpy,
    }


def build_core_buy_materials(
    snapshot: PortfolioSnapshot,
    bucket_allocations: list[BucketAllocation],
    resolved_buckets: dict[str, str],
    market_references: list[MarketReference],
    buy_rules_config: dict,
) -> tuple[dict, list[PortfolioWarning]]:
    reference_map = {reference.symbol: reference for reference in market_references}
    allocations = {allocation.bucket: allocation for allocation in bucket_allocations}
    core_constituents: list[dict] = []
    warnings: list[PortfolioWarning] = []

    for holding in snapshot.holdings:
        if resolved_buckets.get(holding.symbol) != "core":
            continue
        reference = reference_map.get(holding.symbol)
        drawdown_pct = None
        if reference is None:
            warnings.append(
                PortfolioWarning(
                    code="missing_core_market_reference",
                    severity="warning",
                    message=f"Core constituent {holding.symbol} is missing market reference data.",
                    related_symbols=[holding.symbol],
                )
            )
        elif reference.current_price is None or reference.recent_high_63d in (None, Decimal("0")):
            warnings.append(
                PortfolioWarning(
                    code="missing_core_drawdown_reference",
                    severity="warning",
                    message=f"Core constituent {holding.symbol} is missing drawdown reference data.",
                    related_symbols=[holding.symbol],
                )
            )
        else:
            drawdown_pct = quantize(
                ((reference.current_price - reference.recent_high_63d) / reference.recent_high_63d) * Decimal("100"),
                2,
            )

        core_constituents.append(
            {
                "symbol": holding.symbol,
                "name": holding.name,
                "quantity": holding.quantity,
                "value_jpy": holding.market_value_jpy,
                "current_price": holding.current_price,
                "reference_symbol": reference.yfinance_symbol if reference is not None else None,
                "reference_current_price": reference.current_price if reference is not None else None,
                "recent_high_21d": reference.recent_high_21d if reference is not None else None,
                "recent_high_63d": reference.recent_high_63d if reference is not None else None,
                "drawdown_pct_from_recent_high": drawdown_pct,
            }
        )

    budget_policy = buy_rules_config.get("core_budget_policy", {})
    core_allocation = allocations.get("core")
    liquidity_allocation = allocations.get("liquidity")
    budget_plan = determine_core_budget_plan(core_allocation, liquidity_allocation, budget_policy)
    return (
        {
            "core_actual_pct": core_allocation.actual_pct if core_allocation is not None else None,
            "core_target_pct": core_allocation.target_pct if core_allocation is not None else None,
            "core_delta_pct": core_allocation.delta_pct if core_allocation is not None else None,
            "liquidity_actual_pct": liquidity_allocation.actual_pct if liquidity_allocation is not None else None,
            "liquidity_target_pct": liquidity_allocation.target_pct if liquidity_allocation is not None else None,
            "cash_excess_pct": (
                quantize(liquidity_allocation.actual_pct - liquidity_allocation.target_pct, 4)
                if liquidity_allocation is not None and liquidity_allocation.target_pct is not None
                else None
            ),
            "core_bucket_total_jpy": core_allocation.market_value_jpy if core_allocation is not None else Decimal("0"),
            "monthly_core_budget_policy": budget_policy,
            "monthly_core_buy_budget_min_jpy": budget_policy.get("monthly_core_buy_budget_min_jpy"),
            "monthly_core_buy_budget_max_jpy": budget_policy.get("monthly_core_buy_budget_max_jpy"),
            "recommended_monthly_core_buy_budget_jpy": budget_plan["recommended_monthly_core_buy_budget_jpy"],
            "monthly_core_budget_tier": budget_plan["monthly_core_budget_tier"],
            "monthly_core_budget_override_active": budget_plan["monthly_core_budget_override_active"],
            "monthly_core_budget_override_reason": budget_plan["monthly_core_budget_override_reason"],
            "core_constituents": core_constituents,
        },
        warnings,
    )


def determine_core_budget_plan(
    core_allocation: BucketAllocation | None,
    liquidity_allocation: BucketAllocation | None,
    budget_policy: dict,
) -> dict:
    base_budget = budget_policy.get("base_monthly_buy_amount_jpy")
    budget_tiers = budget_policy.get("budget_tiers", {})
    standard_budget = budget_tiers.get("standard", {}).get("budget_jpy", base_budget)
    selected_tier = "standard"
    selected_budget = standard_budget
    override_active = False
    override_reason = None

    if core_allocation is not None and liquidity_allocation is not None:
        override_conditions = budget_policy.get("override_conditions", {})
        core_target = core_allocation.target_pct
        core_actual = core_allocation.actual_pct
        liquidity_target = liquidity_allocation.target_pct
        liquidity_actual = liquidity_allocation.actual_pct
        core_shortfall = (
            quantize(core_target - core_actual, 4)
            if core_target is not None and core_actual is not None and core_actual < core_target
            else Decimal("0")
        )
        cash_excess = (
            quantize(liquidity_actual - liquidity_target, 4)
            if liquidity_target is not None and liquidity_actual is not None and liquidity_actual > liquidity_target
            else Decimal("0")
        )
        required_core_shortfall = to_optional_decimal(override_conditions.get("core_shortfall_pct_gte")) or Decimal("0")
        required_cash_excess = to_optional_decimal(override_conditions.get("cash_excess_pct_gte")) or Decimal("0")
        if core_shortfall >= required_core_shortfall and cash_excess >= required_cash_excess:
            selected_tier = str(override_conditions.get("budget_tier", "aggressive"))
            selected_budget = budget_tiers.get(selected_tier, {}).get(
                "budget_jpy",
                budget_policy.get("monthly_core_buy_budget_max_jpy"),
            )
            override_active = True
            override_reason = str(override_conditions.get("reason_code", "core_budget_override"))

    return {
        "recommended_monthly_core_buy_budget_jpy": selected_budget,
        "monthly_core_budget_tier": selected_tier,
        "monthly_core_budget_override_active": override_active,
        "monthly_core_budget_override_reason": override_reason,
    }


def compute_bucket_warnings(
    *,
    snapshot: PortfolioSnapshot,
    policy_config: dict,
    bucket_values: dict[str, Decimal],
    symbol_weights: dict[str, Decimal],
    bucket_allocations: list[BucketAllocation],
    resolved_buckets: dict[str, str],
) -> list[PortfolioWarning]:
    warnings: list[PortfolioWarning] = []
    bucket_policy = policy_config.get("portfolio_buckets", {})
    risk_limits = policy_config.get("risk_limits", {})
    cash_policy = policy_config.get("cash_policy", {})

    for allocation in bucket_allocations:
        if allocation.preferred_min_pct is not None and allocation.actual_pct < allocation.preferred_min_pct:
            warnings.append(
                PortfolioWarning(
                    code=f"{allocation.bucket}_below_range",
                    severity="info",
                    message=(
                        f"Bucket {allocation.bucket} is below preferred range: "
                        f"{format_pct(allocation.actual_pct)} < {format_pct(allocation.preferred_min_pct)}"
                    ),
                )
            )
        if allocation.preferred_max_pct is not None and allocation.actual_pct > allocation.preferred_max_pct:
            warnings.append(
                PortfolioWarning(
                    code=f"{allocation.bucket}_above_range",
                    severity="warning",
                    message=(
                        f"Bucket {allocation.bucket} is above preferred range: "
                        f"{format_pct(allocation.actual_pct)} > {format_pct(allocation.preferred_max_pct)}"
                    ),
                )
            )

    liquidity_jpy = bucket_values.get("liquidity", Decimal("0"))
    liquidity_target = snapshot.liquidity_target_jpy or to_optional_decimal(
        bucket_policy.get("liquidity", {}).get("min_jpy")
    )
    if liquidity_target is not None and liquidity_jpy < liquidity_target:
        warnings.append(
            PortfolioWarning(
                code="liquidity_floor",
                severity="error",
                message=f"Liquidity is below minimum target: {liquidity_jpy} < {liquidity_target} JPY",
                related_symbols=["liquidity"],
            )
        )

    liquidity_pct = percent(liquidity_jpy, snapshot.total_assets_jpy)
    preferred_cash_range = cash_policy.get("preferred_total_assets_pct_range") or [None, None]
    preferred_cash_min = (
        to_optional_decimal(preferred_cash_range[0]) if preferred_cash_range[0] is not None else None
    )
    preferred_cash_max = (
        to_optional_decimal(preferred_cash_range[1]) if preferred_cash_range[1] is not None else None
    )
    if preferred_cash_min is not None and liquidity_pct < preferred_cash_min:
        warnings.append(
            PortfolioWarning(
                code="cash_below_preferred",
                severity="warning",
                message=(
                    "Liquidity is below preferred total-assets band: "
                    f"{format_pct(liquidity_pct)} < {format_pct(preferred_cash_min)}"
                ),
                related_symbols=["liquidity"],
            )
        )
    if preferred_cash_max is not None and liquidity_pct > preferred_cash_max:
        warnings.append(
            PortfolioWarning(
                code="cash_above_preferred",
                severity="info",
                message=(
                    "Liquidity is above preferred total-assets band: "
                    f"{format_pct(liquidity_pct)} > {format_pct(preferred_cash_max)}"
                ),
                related_symbols=["liquidity"],
            )
        )

    satellite_pct = percent(bucket_values.get("satellite", Decimal("0")), snapshot.total_assets_jpy)
    satellite_core_pct = percent(bucket_values.get("satellite_core", Decimal("0")), snapshot.total_assets_jpy)
    sat_plus_core_limit = to_optional_decimal(risk_limits.get("satellite_plus_satellite_core_max_pct"))
    if sat_plus_core_limit is not None and satellite_pct + satellite_core_pct > sat_plus_core_limit:
        warnings.append(
            PortfolioWarning(
                code="satellite_plus_core_limit",
                severity="warning",
                message=(
                    "Satellite + satellite_core exceeds policy limit: "
                    f"{format_pct(quantize(satellite_pct + satellite_core_pct, 4))} > {format_pct(sat_plus_core_limit)}"
                ),
                related_symbols=["satellite", "satellite_core"],
            )
        )

    satellite_limit = to_optional_decimal(risk_limits.get("satellite_max_pct"))
    if satellite_limit is not None and satellite_pct > satellite_limit:
        warnings.append(
            PortfolioWarning(
                code="satellite_limit",
                severity="warning",
                message=f"Satellite bucket exceeds limit: {format_pct(satellite_pct)} > {format_pct(satellite_limit)}",
                related_symbols=["satellite"],
            )
        )

    pltr_limit = to_optional_decimal(risk_limits.get("pltr_max_total_assets_pct"))
    pltr_weight = symbol_weights.get("PLTR", Decimal("0"))
    if pltr_limit is not None and pltr_weight > pltr_limit:
        warnings.append(
            PortfolioWarning(
                code="pltr_limit",
                severity="warning",
                message=f"PLTR exceeds total-assets cap: {format_pct(pltr_weight)} > {format_pct(pltr_limit)}",
                related_symbols=["PLTR"],
            )
        )

    high_vol_limit = to_optional_decimal(risk_limits.get("single_high_vol_name_max_pct"))
    if high_vol_limit is not None:
        for holding in snapshot.holdings:
            if resolved_buckets.get(holding.symbol) != "satellite":
                continue
            weight = symbol_weights.get(holding.symbol, Decimal("0"))
            if weight > high_vol_limit:
                warnings.append(
                    PortfolioWarning(
                        code="single_high_vol_name_limit",
                        severity="warning",
                        message=(
                            f"High-vol name {holding.symbol} exceeds single-name limit: "
                            f"{format_pct(weight)} > {format_pct(high_vol_limit)}"
                        ),
                        related_symbols=[holding.symbol],
                    )
                )

    return warnings


def format_pct(value: Decimal | None) -> str:
    if value is None:
        return "null"
    return f"{quantize(value * Decimal('100'), 2)}%"
