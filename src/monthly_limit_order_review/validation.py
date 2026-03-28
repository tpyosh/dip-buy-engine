from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from .models import CandidateOrder, PortfolioWarning


def apply_candidate_validations(
    candidate_orders: list[CandidateOrder],
    buy_rules_config: dict,
) -> tuple[list[CandidateOrder], list[PortfolioWarning]]:
    warnings: list[PortfolioWarning] = []
    validated: list[CandidateOrder] = []
    reason_text_map = buy_rules_config.get("validation", {}).get("suppress_reason_text", {})

    for candidate in candidate_orders:
        existing_reason_code = candidate.suppressed_reason_code
        reason_code = existing_reason_code
        if candidate.current_price is None:
            reason_code = "missing_current_price"
        elif candidate.base_price is None or candidate.base_price <= 0:
            reason_code = "invalid_base_price"
        elif candidate.shares <= 0:
            reason_code = "non_positive_shares"
        elif candidate.limit_price is None or candidate.estimated_cost is None or candidate.estimated_cost_jpy is None:
            reason_code = "calculation_unavailable"
        elif candidate.estimated_cost_jpy <= 0 or candidate.estimated_cost <= 0:
            reason_code = "non_positive_est_cost"
        elif candidate.limit_price >= candidate.current_price:
            reason_code = "limit_above_current"

        reason_text = candidate.suppressed_reason_text if reason_code == existing_reason_code else None
        if reason_code is not None and reason_text is None:
            reason_text = reason_text_map.get(reason_code)
        note = candidate.note_for_chatgpt
        if reason_code is not None:
            if note is None or reason_code not in note.split(","):
                note = f"{note},{reason_code}" if note else reason_code
            warnings.append(
                PortfolioWarning(
                    code=reason_code,
                    severity="warning",
                    message=f"{candidate.symbol}: {reason_text}",
                    related_symbols=[candidate.symbol],
                )
            )

        validated.append(
            replace(
                candidate,
                suppressed=candidate.suppressed or reason_code is not None,
                suppressed_reason_code=reason_code,
                suppressed_reason_text=reason_text,
                note_for_chatgpt=note,
                suppression_reasons=(
                    list(dict.fromkeys([*candidate.suppression_reasons, *([reason_text] if reason_text else [])]))
                ),
            )
        )

    return validated, warnings


def build_validation_warnings(snapshot_warnings: list[str]) -> list[PortfolioWarning]:
    normalized: list[PortfolioWarning] = []
    for message in snapshot_warnings:
        code = "snapshot_warning"
        if "missing quantity" in message:
            code = "missing_quantity"
        elif "missing current_price" in message:
            code = "missing_current_price"
        elif "missing avg_cost" in message:
            code = "missing_avg_cost"
        normalized.append(PortfolioWarning(code=code, severity="info", message=message))
    return normalized


def build_exposure_validation_warnings(exposure_breakdown: dict) -> list[PortfolioWarning]:
    warnings: list[PortfolioWarning] = []
    breakdown = exposure_breakdown.get("breakdown", [])
    if not breakdown:
        warnings.append(
            PortfolioWarning(
                code="semiconductor_exposure_definition_missing",
                severity="warning",
                message="Semiconductor exposure breakdown is empty or undefined.",
            )
        )
        return warnings

    included_total = sum(
        (item["value_jpy"] for item in breakdown if item.get("included_in_semiconductor_exposure") == "yes"),
        start=Decimal("0"),
    )
    if included_total != exposure_breakdown.get("semiconductor_exposure_total_jpy"):
        warnings.append(
            PortfolioWarning(
                code="semiconductor_exposure_total_mismatch",
                severity="error",
                message=(
                    "Semiconductor exposure breakdown total does not match summary total: "
                    f"{included_total} vs {exposure_breakdown.get('semiconductor_exposure_total_jpy')}"
                ),
            )
        )
    return warnings
