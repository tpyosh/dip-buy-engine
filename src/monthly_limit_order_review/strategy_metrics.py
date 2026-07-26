from __future__ import annotations

from decimal import Decimal

from .models import BucketAllocation, PortfolioSnapshot, PortfolioWarning
from .utils import percent, quantize, to_optional_decimal


ACTIVE_PLAN_STATUSES = {"approved_pending_execution", "active"}


def compute_strategy_allocations(
    snapshot: PortfolioSnapshot,
    bucket_values: dict[str, Decimal],
    strategy: dict,
    active_plans: list[dict] | None = None,
) -> dict:
    groups = strategy.get("allocation", {}).get("target_groups", {})
    reserved_cash_jpy = active_reserved_cash_jpy(active_plans or [])
    liquidity_jpy = bucket_values.get("liquidity", Decimal("0"))
    recognized_reserved_cash_jpy = min(reserved_cash_jpy, liquidity_jpy)

    allocations: list[BucketAllocation] = []
    group_values: dict[str, Decimal] = {}
    for group_name, group_policy in groups.items():
        value = sum(
            (bucket_values.get(bucket, Decimal("0")) for bucket in group_policy.get("member_buckets", [])),
            start=Decimal("0"),
        )
        if group_name == "active_hobby" and group_policy.get("reserved_cash_counts_from_approval"):
            value += recognized_reserved_cash_jpy
        group_values[group_name] = value

        target_pct = to_optional_decimal(group_policy.get("target_pct"))
        actual_pct = percent(value, snapshot.total_assets_jpy)
        allocations.append(
            BucketAllocation(
                bucket=group_name,
                market_value_jpy=value,
                actual_pct=actual_pct,
                target_pct=target_pct,
                delta_pct=(
                    quantize(actual_pct - target_pct, 4)
                    if target_pct is not None
                    else None
                ),
                preferred_min_pct=to_optional_decimal(
                    group_policy.get("rebalance_proposal_below_pct")
                ),
                preferred_max_pct=to_optional_decimal(
                    group_policy.get("rebalance_proposal_above_pct")
                ),
            )
        )

    unallocated_liquidity_jpy = max(
        Decimal("0"),
        liquidity_jpy - recognized_reserved_cash_jpy,
    )
    classified_group_total_jpy = sum(group_values.values(), start=Decimal("0"))
    residual_jpy = snapshot.total_assets_jpy - classified_group_total_jpy - unallocated_liquidity_jpy

    return {
        "allocations": allocations,
        "group_values": group_values,
        "reserved_cash_jpy": reserved_cash_jpy,
        "recognized_reserved_cash_jpy": recognized_reserved_cash_jpy,
        "unallocated_liquidity_jpy": unallocated_liquidity_jpy,
        "residual_jpy": residual_jpy,
    }


def build_strategy_warnings(
    *,
    strategy: dict,
    strategy_metrics: dict,
    exposure_breakdown: dict,
    symbol_weights: dict[str, Decimal],
) -> list[PortfolioWarning]:
    warnings: list[PortfolioWarning] = []
    allocation_map = {
        allocation.bucket: allocation
        for allocation in strategy_metrics.get("allocations", [])
    }

    broad_core = allocation_map.get("broad_core")
    if (
        broad_core is not None
        and broad_core.preferred_min_pct is not None
        and broad_core.actual_pct < broad_core.preferred_min_pct
    ):
        warnings.append(
            PortfolioWarning(
                code="broad_core_reinforcement_proposal",
                severity="warning",
                message=(
                    "Broad core is below the reinforcement proposal threshold: "
                    f"{_format_pct(broad_core.actual_pct)} < "
                    f"{_format_pct(broad_core.preferred_min_pct)}"
                ),
                related_symbols=["broad_core"],
            )
        )

    active_hobby = allocation_map.get("active_hobby")
    if (
        active_hobby is not None
        and active_hobby.preferred_max_pct is not None
        and active_hobby.actual_pct > active_hobby.preferred_max_pct
    ):
        warnings.append(
            PortfolioWarning(
                code="active_hobby_rebalance_proposal",
                severity="warning",
                message=(
                    "Active/hobby is above the rebalance proposal threshold: "
                    f"{_format_pct(active_hobby.actual_pct)} > "
                    f"{_format_pct(active_hobby.preferred_max_pct)}"
                ),
                related_symbols=["active_hobby"],
            )
        )

    if strategy_metrics.get("reserved_cash_jpy", Decimal("0")) > strategy_metrics.get(
        "recognized_reserved_cash_jpy",
        Decimal("0"),
    ):
        warnings.append(
            PortfolioWarning(
                code="reserved_hobby_cash_shortfall",
                severity="error",
                message="Liquidity is below the approved active/hobby reserved-cash amount.",
                related_symbols=["liquidity", "active_hobby"],
            )
        )

    semiconductor_policy = (
        strategy.get("risk_limits", {})
        .get("direct_themes", {})
        .get("semiconductor", {})
    )
    direct_semiconductor_pct = exposure_breakdown.get(
        "direct_semiconductor_exposure_pct",
        Decimal("0"),
    )
    semi_preferred_max = to_optional_decimal(
        semiconductor_policy.get("preferred_max_pct")
    )
    semi_rebalance = to_optional_decimal(
        semiconductor_policy.get("rebalance_proposal_above_pct")
    )
    if (
        semi_rebalance is not None
        and direct_semiconductor_pct > semi_rebalance
    ):
        warnings.append(
            PortfolioWarning(
                code="semiconductor_rebalance_proposal",
                severity="warning",
                message=(
                    "Direct semiconductor exposure is above the rebalance proposal threshold: "
                    f"{_format_pct(direct_semiconductor_pct)} > {_format_pct(semi_rebalance)}"
                ),
                related_symbols=["direct_semiconductor"],
            )
        )
    elif (
        semi_preferred_max is not None
        and direct_semiconductor_pct > semi_preferred_max
    ):
        warnings.append(
            PortfolioWarning(
                code="semiconductor_routine_additions_paused",
                severity="info",
                message=(
                    "Direct semiconductor exposure is above the routine-addition limit: "
                    f"{_format_pct(direct_semiconductor_pct)} > "
                    f"{_format_pct(semi_preferred_max)}"
                ),
                related_symbols=["direct_semiconductor"],
            )
        )

    high_volatility_policy = (
        strategy.get("risk_limits", {})
        .get("high_volatility_single_security", {})
    )
    high_vol_preferred_max = to_optional_decimal(
        high_volatility_policy.get("preferred_max_pct")
    )
    high_vol_rebalance = to_optional_decimal(
        high_volatility_policy.get("rebalance_proposal_above_pct")
    )
    for symbol in high_volatility_policy.get("symbols", []):
        weight = symbol_weights.get(str(symbol), Decimal("0"))
        if high_vol_rebalance is not None and weight > high_vol_rebalance:
            warnings.append(
                PortfolioWarning(
                    code="high_volatility_rebalance_proposal",
                    severity="warning",
                    message=(
                        f"High-volatility security {symbol} is above the rebalance proposal threshold: "
                        f"{_format_pct(weight)} > {_format_pct(high_vol_rebalance)}"
                    ),
                    related_symbols=[str(symbol)],
                )
            )
        elif high_vol_preferred_max is not None and weight > high_vol_preferred_max:
            warnings.append(
                PortfolioWarning(
                    code="high_volatility_routine_additions_paused",
                    severity="info",
                    message=(
                        f"High-volatility security {symbol} is above the routine-addition limit: "
                        f"{_format_pct(weight)} > {_format_pct(high_vol_preferred_max)}"
                    ),
                    related_symbols=[str(symbol)],
                )
            )

    return warnings


def active_reserved_cash_jpy(active_plans: list[dict]) -> Decimal:
    total = Decimal("0")
    for plan in active_plans:
        if plan.get("status") not in ACTIVE_PLAN_STATUSES:
            continue
        reserve = (
            plan.get("allocations", {})
            .get("hobby_dip_buy_reserve", {})
            .get("amount_jpy")
        )
        if reserve is not None:
            total += Decimal(str(reserve))
    return total


def get_active_core_deployment_plan(active_plans: list[dict]) -> dict | None:
    for plan in active_plans:
        if plan.get("status") not in ACTIVE_PLAN_STATUSES:
            continue
        core_allocation = (
            plan.get("allocations", {})
            .get("broad_core_lump_sum")
        )
        if core_allocation:
            return {
                "plan_id": plan.get("plan_id"),
                "status": plan.get("status"),
                "basis": plan.get("basis", {}),
                "allocation": core_allocation,
                "execution_gate": plan.get("execution_gate", {}),
            }
    return None


def _format_pct(value: Decimal) -> str:
    return f"{quantize(value * Decimal('100'), 2)}%"
