from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import BucketAllocation, Holding, PortfolioSnapshot, PortfolioWarning
from .utils import percent, quantize, to_optional_decimal

SEMICONDUCTOR_SYMBOL_KEYWORDS = ("SOX", "SMH", "SOXX", "SEMICONDUCTOR")
SEMICONDUCTOR_NAME_KEYWORDS = ("SOX", "半導体", "SEMICONDUCTOR")


def analyze_portfolio(snapshot: PortfolioSnapshot, policy_config: dict) -> dict:
    bucket_values: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    symbol_weights: dict[str, Decimal] = {}
    semiconductor_symbols: list[str] = []
    resolved_buckets: dict[str, str] = {}

    for holding in snapshot.holdings:
        bucket = resolve_bucket(holding.symbol, holding.asset_class, policy_config, holding.name)
        bucket_values[bucket] += holding.market_value_jpy
        symbol_weights[holding.symbol] = percent(holding.market_value_jpy, snapshot.total_assets_jpy)
        resolved_buckets[holding.symbol] = bucket
        if is_semiconductor_holding(holding):
            semiconductor_symbols.append(holding.symbol)

    bucket_allocations = build_bucket_allocations(snapshot, policy_config, bucket_values)
    warnings = build_portfolio_warnings(snapshot, policy_config, bucket_values, symbol_weights, bucket_allocations)
    semi_exposure_pct = calculate_semiconductor_exposure(snapshot)
    liquidity_jpy = bucket_values.get("liquidity", Decimal("0"))

    risk_limits = policy_config.get("risk_limits", {})
    semi_limit = to_optional_decimal(risk_limits.get("semi_exposure_max_pct_of_total_assets"))
    if semi_limit is not None and semi_exposure_pct > semi_limit:
        warnings.append(
            PortfolioWarning(
                code="semi_exposure_limit",
                severity="warning",
                related_symbols=sorted(set(semiconductor_symbols)),
                message=(
                    "Semiconductor exposure exceeds policy cap: "
                    f"{format_pct(semi_exposure_pct)} > {format_pct(semi_limit)}"
                ),
            )
        )

    return {
        "bucket_allocations": bucket_allocations,
        "warnings": warnings,
        "semi_exposure_pct": semi_exposure_pct,
        "liquidity_jpy": liquidity_jpy,
        "symbol_weights": symbol_weights,
        "resolved_buckets": resolved_buckets,
    }


def resolve_bucket(symbol: str, asset_class: str, policy_config: dict, name: str = "") -> str:
    explicit_bucket = policy_config.get("symbol_to_bucket", {}).get(symbol)
    if explicit_bucket is not None:
        return explicit_bucket
    if is_semiconductor_identifier(symbol, name):
        return "satellite_core"
    return asset_class


def build_bucket_allocations(
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


def calculate_semiconductor_exposure(snapshot: PortfolioSnapshot) -> Decimal:
    semi_value = sum(
        (holding.market_value_jpy for holding in snapshot.holdings if is_semiconductor_holding(holding)),
        start=Decimal("0"),
    )
    return percent(semi_value, snapshot.total_assets_jpy)


def build_portfolio_warnings(
    snapshot: PortfolioSnapshot,
    policy_config: dict,
    bucket_values: dict[str, Decimal],
    symbol_weights: dict[str, Decimal],
    bucket_allocations: list[BucketAllocation],
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
                severity="critical",
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
            bucket = resolve_bucket(holding.symbol, holding.asset_class, policy_config, holding.name)
            if bucket != "satellite":
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


def format_pct(value: Decimal) -> str:
    return f"{quantize(value * Decimal('100'), 2)}%"


def is_semiconductor_holding(holding: Holding) -> bool:
    return is_semiconductor_identifier(holding.symbol, holding.name)


def is_semiconductor_identifier(symbol: str, name: str) -> bool:
    symbol_upper = symbol.upper()
    name_upper = name.upper()
    return any(keyword in symbol_upper for keyword in SEMICONDUCTOR_SYMBOL_KEYWORDS) or any(
        keyword in name_upper or keyword in name for keyword in SEMICONDUCTOR_NAME_KEYWORDS
    )
