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
    mode_context: dict | None = None,
) -> list[CandidateOrder]:
    reference_map = {reference.symbol: reference for reference in market_references}
    round_rules = buy_rules_config.get("execution", {}).get("round_price", {})
    actual_pct_by_bucket = {allocation.bucket: allocation.actual_pct for allocation in bucket_allocations}
    target_pct_by_bucket = {allocation.bucket: allocation.target_pct for allocation in bucket_allocations}
    usd_jpy = reference_map.get("USDJPY")
    candidate_policy = buy_rules_config.get("candidate_policy", {})
    active_mode = resolve_candidate_mode(mode_context)
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
        base_price = (reference.mean_close_30d or reference.mean_close_20d) if reference is not None else None
        avg20_base_price = reference.mean_close_20d if reference is not None else None
        current_price = reference.current_price if reference is not None else None

        for tranche in rule_config.get("tranches", []):
            drawdown_pct = to_decimal(tranche["drawdown_pct"], field_name=f"{symbol}.drawdown_pct")
            shares = int(tranche["shares"])
            limit_price = None
            estimated_cost = None
            estimated_cost_jpy = None
            avg20_gap_pct = None
            if base_price is not None:
                limit_price = quantize(
                    base_price * (Decimal("1") + (drawdown_pct / Decimal("100"))),
                    digits,
                )
            if limit_price is not None and avg20_base_price not in (None, Decimal("0")):
                avg20_gap_pct = quantize(((limit_price / avg20_base_price) - Decimal("1")) * Decimal("100"), 2)
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
                active_mode=active_mode,
            )
            notes.extend(policy_outcome["notes"])
            mode_priority_weight = get_mode_priority_weight(
                active_mode=active_mode,
                bucket=bucket,
                candidate_policy=candidate_policy,
            )
            notes.extend(build_mode_notes(active_mode=active_mode, bucket=bucket, priority_weight=mode_priority_weight))
            explanation = build_candidate_explanation(
                policy_outcome=policy_outcome,
                active_mode=active_mode,
                bucket=bucket,
                actual_pct=actual_pct_by_bucket.get(bucket),
                target_pct=target_pct_by_bucket.get(bucket),
                mode_priority_weight=mode_priority_weight,
            )
            candidates.append(
                CandidateOrder(
                    symbol=symbol,
                    bucket=bucket,
                    base_price=base_price,
                    avg20_base_price=avg20_base_price,
                    current_price=current_price,
                    limit_price=limit_price,
                    shares=shares,
                    estimated_cost=estimated_cost,
                    estimated_cost_jpy=estimated_cost_jpy,
                    currency=currency,
                    drawdown_pct=drawdown_pct,
                    drawdown_rule=f"{drawdown_pct}% x {shares}",
                    reference_method="mean_close_30d",
                    suppressed=policy_outcome["suppressed"],
                    suppressed_reason_code=policy_outcome["suppressed_reason_code"],
                    suppressed_reason_text=policy_outcome["suppressed_reason_text"],
                    note_for_chatgpt=",".join(unique_notes(notes)) if notes else None,
                    avg20_gap_pct=avg20_gap_pct,
                    suppression_reasons=(
                        [policy_outcome["suppressed_reason_text"]]
                        if policy_outcome["suppressed_reason_text"] is not None
                        else []
                    ),
                    explanation=explanation,
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
    drawdown_profile = classify_drawdown_profile(symbol=symbol, bucket=bucket, drawdown_pct=drawdown_pct)
    notes.append(f"drawdown_profile:{drawdown_profile}")
    if drawdown_profile == "shallow":
        notes.append("shallow_candidate")
    elif drawdown_profile == "deep":
        notes.append("deep_drawdown_candidate")
    if bucket == "satellite":
        notes.append("high_volatility_name")
    if actual_pct is not None and target_pct is not None and actual_pct > target_pct:
        notes.append("bucket_over_target")
    if symbol == "PLTR" and "high_volatility_name" not in notes:
        notes.append("high_volatility_name")
    return notes


def classify_drawdown_profile(*, symbol: str, bucket: str, drawdown_pct: Decimal) -> str:
    if symbol == "PLTR" or bucket == "satellite":
        return "deep" if drawdown_pct <= Decimal("-12") else "shallow"
    return "deep" if drawdown_pct <= Decimal("-15") else "shallow"


def build_candidate_policy_outcome(
    *,
    symbol: str,
    bucket: str,
    drawdown_pct: Decimal,
    actual_pct: Decimal | None,
    target_pct: Decimal | None,
    candidate_policy: dict,
    active_mode: str,
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
        notes.append(f"bucket_over_target_deep_threshold_pct:{deep_threshold}")
        if behavior == "deep_only":
            if drawdown_pct > deep_threshold:
                notes.append(str(bucket_policy.get("deep_only_note", "default_deep_only_due_to_bucket_over_target")))
                suppressed = True
                suppressed_reason_code = str(
                    bucket_policy.get("suppressed_reason_code", "bucket_over_target_shallow_suppressed")
                )
                suppressed_reason_text = str(
                    bucket_policy.get(
                        "suppressed_reason_text",
                        "Shallow candidate suppressed because related bucket is over target.",
                    )
                )
            else:
                notes.append(str(bucket_policy.get("allow_note", "default_allow_deep_drawdown_even_if_bucket_over_target")))
        elif behavior == "skip":
            notes.append(str(bucket_policy.get("skip_note", "default_skip_due_to_bucket_over_target")))
            suppressed = True
            suppressed_reason_code = str(bucket_policy.get("suppressed_reason_code", "bucket_over_target_suppressed"))
            suppressed_reason_text = str(
                bucket_policy.get("suppressed_reason_text", "Candidate suppressed because related bucket is over target.")
            )
        else:
            notes.append("default_deprioritize_due_to_bucket_over_target")

    high_volatility_policy = candidate_policy.get("high_volatility", {})
    high_vol_symbols = {item.upper() for item in high_volatility_policy.get("symbols", [])}
    shallow_threshold = to_decimal(
        high_volatility_policy.get("shallow_drawdown_threshold_pct", -12),
        field_name="candidate_policy.high_volatility.shallow_drawdown_threshold_pct",
    )
    if symbol.upper() in high_vol_symbols:
        notes.append(f"high_volatility_shallow_threshold_pct:{shallow_threshold}")
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
        "active_mode": active_mode,
    }


def resolve_candidate_mode(mode_context: dict | None) -> str:
    if not mode_context:
        return "normal"
    mode = str(mode_context.get("portfolio_management_mode") or "normal")
    if mode == "rebalance":
        return "rebalance"
    if mode == "risk_off":
        return "risk_off"
    return "normal"


def get_mode_priority_weight(*, active_mode: str, bucket: str, candidate_policy: dict) -> int:
    mode_priority = candidate_policy.get("mode_priority", {})
    weights = mode_priority.get(active_mode, mode_priority.get("normal", {}))
    raw_weight = weights.get(bucket, 0)
    return int(raw_weight)


def build_mode_notes(*, active_mode: str, bucket: str, priority_weight: int) -> list[str]:
    notes: list[str] = []
    notes.append(f"mode_context:{active_mode}")
    notes.append(f"mode_priority_weight:{priority_weight}")
    if active_mode == "rebalance" and bucket in {"core", "jun_core"}:
        notes.append("mode_rebalance_priority_boost")
    if active_mode == "rebalance" and bucket not in {"core", "jun_core"} and priority_weight < 0:
        notes.append("mode_rebalance_relative_deprioritization")
    return notes


def build_candidate_explanation(
    *,
    policy_outcome: dict,
    active_mode: str,
    bucket: str,
    actual_pct: Decimal | None,
    target_pct: Decimal | None,
    mode_priority_weight: int,
) -> dict:
    related_bucket_status = {
        "bucket": bucket,
        "actual_pct": actual_pct,
        "target_pct": target_pct,
        "is_over_target": (
            bool(actual_pct is not None and target_pct is not None and actual_pct > target_pct)
            if actual_pct is not None and target_pct is not None
            else False
        ),
    }
    return {
        "rule_based_reason": policy_outcome.get("notes", []),
        "discretionary_reason": None,
        "related_bucket_status": related_bucket_status,
        "mode_context": {
            "active_mode": active_mode,
            "priority_weight": mode_priority_weight,
        },
        "suppression": {
            "suppressed": policy_outcome.get("suppressed", False),
            "reason_code": policy_outcome.get("suppressed_reason_code"),
            "reason_text": policy_outcome.get("suppressed_reason_text"),
        },
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
