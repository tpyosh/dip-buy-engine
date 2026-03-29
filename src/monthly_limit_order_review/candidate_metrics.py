from __future__ import annotations

from decimal import Decimal

from .models import CandidateOrder, MarketReference, PortfolioSnapshot
from .utils import quantize, to_decimal


def compute_candidate_metrics(
    snapshot: PortfolioSnapshot,
    buy_rules_config: dict,
    portfolio_policy: dict,
    market_references: list[MarketReference],
    resolved_buckets: dict[str, str],
    bucket_allocations: list,
) -> list[CandidateOrder]:
    reference_map = {reference.symbol: reference for reference in market_references}
    round_rules = buy_rules_config.get("execution", {}).get("round_price", {})
    actual_pct_by_bucket = {allocation.bucket: allocation.actual_pct for allocation in bucket_allocations}
    target_pct_by_bucket = {allocation.bucket: allocation.target_pct for allocation in bucket_allocations}
    usd_jpy = reference_map.get("USDJPY")
    candidate_policy = buy_rules_config.get("candidate_policy", {})
    candidates: list[CandidateOrder] = []

    for symbol, rule_config in buy_rules_config.get("limit_order_rules", {}).items():
        reference = reference_map.get(symbol)
        current_holding = next((holding for holding in snapshot.holdings if holding.symbol == symbol), None)
        bucket = resolved_buckets.get(symbol)
        if bucket is None and current_holding is not None:
            bucket = current_holding.asset_class
        if bucket is None:
            bucket = portfolio_policy.get("symbol_to_bucket", {}).get(symbol, "unknown")

        currency = reference.currency if reference is not None else (current_holding.currency if current_holding else "USD")
        digits = int(round_rules.get("jpy_decimals" if currency == "JPY" else "usd_decimals", 2))
        base_price = reference.mean_close_20d if reference is not None else None
        current_price = reference.current_price if reference is not None else None

        for tranche in rule_config.get("tranches", []):
            drawdown_pct = to_decimal(tranche["drawdown_pct"], field_name=f"{symbol}.drawdown_pct")
            shares = int(tranche["shares"])
            limit_price = None
            estimated_cost = None
            estimated_cost_jpy = None
            if base_price is not None:
                limit_price = quantize(
                    base_price * (Decimal("1") + (drawdown_pct / Decimal("100"))),
                    digits,
                )
            if limit_price is not None:
                estimated_cost = quantize(limit_price * Decimal(shares), digits)
                estimated_cost_jpy = estimate_cost_jpy(estimated_cost, currency, usd_jpy)

            notes = build_candidate_notes(
                symbol=symbol,
                bucket=bucket,
                drawdown_pct=drawdown_pct,
                actual_pct=actual_pct_by_bucket.get(bucket),
                target_pct=target_pct_by_bucket.get(bucket),
            )
            policy_outcome = build_candidate_policy_outcome(
                symbol=symbol,
                bucket=bucket,
                drawdown_pct=drawdown_pct,
                actual_pct=actual_pct_by_bucket.get(bucket),
                target_pct=target_pct_by_bucket.get(bucket),
                candidate_policy=candidate_policy,
            )
            notes.extend(policy_outcome["notes"])
            candidates.append(
                CandidateOrder(
                    symbol=symbol,
                    bucket=bucket,
                    base_price=base_price,
                    current_price=current_price,
                    limit_price=limit_price,
                    shares=shares,
                    estimated_cost=estimated_cost,
                    estimated_cost_jpy=estimated_cost_jpy,
                    currency=currency,
                    drawdown_pct=drawdown_pct,
                    drawdown_rule=f"{drawdown_pct}% x {shares}",
                    reference_method="mean_close_20d",
                    suppressed=policy_outcome["suppressed"],
                    suppressed_reason_code=policy_outcome["suppressed_reason_code"],
                    suppressed_reason_text=policy_outcome["suppressed_reason_text"],
                    note_for_chatgpt=",".join(unique_notes(notes)) if notes else None,
                    suppression_reasons=(
                        [policy_outcome["suppressed_reason_text"]]
                        if policy_outcome["suppressed_reason_text"] is not None
                        else []
                    ),
                )
            )

    return candidates


def build_candidate_notes(
    *,
    symbol: str,
    bucket: str,
    drawdown_pct: Decimal,
    actual_pct: Decimal | None,
    target_pct: Decimal | None,
) -> list[str]:
    notes: list[str] = []
    if drawdown_pct >= Decimal("-6"):
        notes.append("shallow_candidate")
    if drawdown_pct <= Decimal("-15"):
        notes.append("deep_drawdown_candidate")
    if bucket == "satellite":
        notes.append("high_volatility_name")
    if actual_pct is not None and target_pct is not None and actual_pct > target_pct:
        notes.append("bucket_over_target")
    if symbol == "PLTR" and "high_volatility_name" not in notes:
        notes.append("high_volatility_name")
    return notes


def build_candidate_policy_outcome(
    *,
    symbol: str,
    bucket: str,
    drawdown_pct: Decimal,
    actual_pct: Decimal | None,
    target_pct: Decimal | None,
    candidate_policy: dict,
) -> dict:
    notes: list[str] = []
    suppressed = False
    suppressed_reason_code = None
    suppressed_reason_text = None

    bucket_policy = candidate_policy.get("bucket_over_target", {})
    if actual_pct is not None and target_pct is not None and actual_pct > target_pct:
        behavior = str(bucket_policy.get("default_behavior", "deprioritize"))
        deviation = actual_pct - target_pct
        deviation_level = "high" if deviation >= Decimal("0.10") else "medium" if deviation >= Decimal("0.05") else "low"
        notes.append(f"auto_tranche_adjustment_bucket_over_target:{deviation_level}")
        deep_threshold = to_decimal(
            bucket_policy.get("deep_drawdown_threshold_pct", -15),
            field_name="candidate_policy.bucket_over_target.deep_drawdown_threshold_pct",
        )
        if behavior == "deep_only":
            if drawdown_pct > deep_threshold:
                notes.append(str(bucket_policy.get("deep_only_note", "default_deep_only_due_to_bucket_over_target")))
            else:
                notes.append(str(bucket_policy.get("allow_note", "default_allow_deep_drawdown_even_if_bucket_over_target")))
        elif behavior == "skip":
            notes.append(str(bucket_policy.get("skip_note", "default_skip_due_to_bucket_over_target")))
        else:
            notes.append("default_deprioritize_due_to_bucket_over_target")

    high_volatility_policy = candidate_policy.get("high_volatility", {})
    high_vol_symbols = {item.upper() for item in high_volatility_policy.get("symbols", [])}
    shallow_threshold = to_decimal(
        high_volatility_policy.get("shallow_drawdown_threshold_pct", -12),
        field_name="candidate_policy.high_volatility.shallow_drawdown_threshold_pct",
    )
    if symbol.upper() in high_vol_symbols and bool(high_volatility_policy.get("suppress_shallow_candidates", False)):
        if drawdown_pct > shallow_threshold:
            suppressed = True
            suppressed_reason_code = str(
                high_volatility_policy.get("suppressed_reason_code", "high_volatility_shallow_suppressed")
            )
            suppressed_reason_text = str(
                high_volatility_policy.get(
                    "suppressed_reason_text",
                    "High-volatility names default to deeper pullbacks before adding.",
                )
            )
            notes.append("rule_based_high_volatility_shallow_suppression")

    return {
        "notes": notes,
        "suppressed": suppressed,
        "suppressed_reason_code": suppressed_reason_code,
        "suppressed_reason_text": suppressed_reason_text,
    }


def unique_notes(notes: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for note in notes:
        if note in seen:
            continue
        seen.add(note)
        ordered.append(note)
    return ordered


def estimate_cost_jpy(
    estimated_cost: Decimal,
    currency: str,
    usd_jpy_reference: MarketReference | None,
) -> Decimal | None:
    if currency == "JPY":
        return quantize(estimated_cost, 0)
    if currency == "USD" and usd_jpy_reference is not None and usd_jpy_reference.current_price is not None:
        return quantize(estimated_cost * usd_jpy_reference.current_price, 0)
    return None
