from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from decimal import Decimal

from .models import CandidateOrder, PortfolioSnapshot, PortfolioWarning


VALID_CURRENCIES = {"JPY", "USD"}
CATEGORY_TOTAL_TOLERANCE_JPY = Decimal("100")
CATEGORY_TOTAL_TOLERANCE_PCT = Decimal("0.001")
DISAPPEARANCE_VALUE_THRESHOLD_JPY = Decimal("10000")
MONTH_OVER_MONTH_CHANGE_ABS_THRESHOLD_JPY = Decimal("1000000")
MONTH_OVER_MONTH_CHANGE_PCT_THRESHOLD = Decimal("0.50")


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
        if "Sum of holding market values" in message:
            code = "total_assets_mismatch"
        elif "missing quantity" in message:
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


def build_ocr_snapshot_validation_warnings(
    snapshot: PortfolioSnapshot,
    *,
    previous_snapshot: PortfolioSnapshot | None = None,
    classification_audit: list[dict] | None = None,
) -> list[PortfolioWarning]:
    warnings: list[PortfolioWarning] = []
    warnings.extend(validate_source_evidence(snapshot))
    warnings.extend(validate_category_totals(snapshot))
    warnings.extend(validate_currency_consistency(snapshot))
    warnings.extend(validate_duplicate_holdings(snapshot))
    warnings.extend(validate_account_type_classification(snapshot, classification_audit or []))
    warnings.extend(validate_classification_audit(classification_audit or []))
    if previous_snapshot is not None:
        warnings.extend(validate_previous_snapshot_continuity(snapshot, previous_snapshot))
    return warnings


def validate_source_evidence(snapshot: PortfolioSnapshot) -> list[PortfolioWarning]:
    evidence = snapshot.source_evidence or {}
    if not evidence:
        return []

    warnings: list[PortfolioWarning] = []
    primary_source = str(evidence.get("primary_source") or evidence.get("primary") or "").lower()
    if primary_source and "screenshot" not in primary_source and "image" not in primary_source:
        warnings.append(
            PortfolioWarning(
                code="primary_evidence_not_screenshot",
                severity="warning",
                message=(
                    "source_evidence.primary_source is not a Money Forward screenshot/image; "
                    "pasted text must remain auxiliary evidence."
                ),
            )
        )
    return warnings


def validate_category_totals(snapshot: PortfolioSnapshot) -> list[PortfolioWarning]:
    if not snapshot.category_totals_jpy:
        return []

    item_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    source_category_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for holding in snapshot.holdings:
        item_totals[holding.asset_class] += holding.market_value_jpy
        if holding.source_category:
            source_category_totals[holding.source_category] += holding.market_value_jpy

    warnings: list[PortfolioWarning] = []
    for category, expected_total in snapshot.category_totals_jpy.items():
        actual_total = source_category_totals.get(category, item_totals.get(category, Decimal("0")))
        gap = actual_total - expected_total
        tolerance = max(CATEGORY_TOTAL_TOLERANCE_JPY, abs(expected_total) * CATEGORY_TOTAL_TOLERANCE_PCT)
        if abs(gap) > tolerance:
            warnings.append(
                PortfolioWarning(
                    code="category_total_mismatch",
                    severity="warning",
                    message=(
                        f"Category total for {category} does not match item total: "
                        f"items={actual_total}, category_total={expected_total}, gap={gap}."
                    ),
                )
            )
    return warnings


def validate_currency_consistency(snapshot: PortfolioSnapshot) -> list[PortfolioWarning]:
    warnings: list[PortfolioWarning] = []
    if snapshot.currency_base != "JPY":
        warnings.append(
            PortfolioWarning(
                code="unexpected_currency_base",
                severity="warning",
                message=f"currency_base is {snapshot.currency_base}; this repository expects JPY as base currency.",
            )
        )
    for holding in snapshot.holdings:
        if holding.currency not in VALID_CURRENCIES:
            warnings.append(
                PortfolioWarning(
                    code="unexpected_holding_currency",
                    severity="warning",
                    message=f"{holding.symbol}: currency is {holding.currency}; expected one of {sorted(VALID_CURRENCIES)}.",
                    related_symbols=[holding.symbol],
                )
            )
    return warnings


def validate_duplicate_holdings(snapshot: PortfolioSnapshot) -> list[PortfolioWarning]:
    warnings: list[PortfolioWarning] = []
    symbol_counts = Counter(holding.symbol for holding in snapshot.holdings)
    for symbol, count in symbol_counts.items():
        if count > 1:
            warnings.append(
                PortfolioWarning(
                    code="duplicate_holding_symbol",
                    severity="warning",
                    message=f"{symbol}: appears {count} times. Verify this is not duplicate OCR/copy-paste overlap.",
                    related_symbols=[symbol],
                )
            )

    identity_counts = Counter(
        (
            normalize_identity_text(holding.name),
            normalize_identity_text(holding.institution),
            normalize_identity_text(holding.account_type),
            holding.market_value_jpy,
        )
        for holding in snapshot.holdings
    )
    for holding in snapshot.holdings:
        key = (
            normalize_identity_text(holding.name),
            normalize_identity_text(holding.institution),
            normalize_identity_text(holding.account_type),
            holding.market_value_jpy,
        )
        if identity_counts[key] > 1 and key[0]:
            warnings.append(
                PortfolioWarning(
                    code="possible_duplicate_holding",
                    severity="warning",
                    message=(
                        f"{holding.symbol}: same name/account/institution/value appears multiple times. "
                        "Confirm screenshots before counting both entries."
                    ),
                    related_symbols=[holding.symbol],
                )
            )
    return dedupe_warnings(warnings)


def validate_account_type_classification(
    snapshot: PortfolioSnapshot,
    classification_audit: list[dict],
) -> list[PortfolioWarning]:
    resolved_bucket_by_symbol = {
        str(item["symbol"]): str(item["resolved_bucket"])
        for item in classification_audit
        if "symbol" in item and "resolved_bucket" in item
    }
    warnings: list[PortfolioWarning] = []
    for holding in snapshot.holdings:
        bucket = resolved_bucket_by_symbol.get(holding.symbol, holding.asset_class)
        account_type = holding.account_type or ""
        searchable = " ".join(
            value
            for value in [holding.symbol, holding.name, holding.asset_class, account_type]
            if value
        ).lower()

        if contains_any(searchable, ("ideco", "年金", "確定拠出")) and bucket != "pension":
            warnings.append(
                PortfolioWarning(
                    code="pension_classification_check",
                    severity="warning",
                    message=f"{holding.symbol}: account/name looks pension-like but resolved bucket is {bucket}.",
                    related_symbols=[holding.symbol],
                )
            )
        if contains_any(account_type, ("NISA", "特定")) and bucket == "pension":
            warnings.append(
                PortfolioWarning(
                    code="account_type_pension_conflict",
                    severity="warning",
                    message=f"{holding.symbol}: account_type={account_type} conflicts with pension bucket.",
                    related_symbols=[holding.symbol],
                )
            )
        if contains_any(searchable, ("cash", "現金", "預金", "普通預金")) and bucket != "liquidity":
            warnings.append(
                PortfolioWarning(
                    code="liquidity_classification_check",
                    severity="warning",
                    message=f"{holding.symbol}: name/account looks liquidity-like but resolved bucket is {bucket}.",
                    related_symbols=[holding.symbol],
                )
            )
    return warnings


def validate_classification_audit(classification_audit: list[dict]) -> list[PortfolioWarning]:
    warnings: list[PortfolioWarning] = []
    for item in classification_audit:
        raw_bucket = item.get("raw_bucket")
        resolved_bucket = item.get("resolved_bucket")
        symbol = str(item.get("symbol"))
        if raw_bucket is not None and resolved_bucket is not None and raw_bucket != resolved_bucket:
            warnings.append(
                PortfolioWarning(
                    code="asset_class_resolved_by_rules",
                    severity="info",
                    message=(
                        f"{symbol}: raw asset_class={raw_bucket} was resolved to {resolved_bucket} "
                        f"by {item.get('reason')}."
                    ),
                    related_symbols=[symbol],
                )
            )
    return warnings


def validate_previous_snapshot_continuity(
    snapshot: PortfolioSnapshot,
    previous_snapshot: PortfolioSnapshot,
) -> list[PortfolioWarning]:
    previous_by_symbol = {holding.symbol: holding for holding in previous_snapshot.holdings}
    current_by_symbol = {holding.symbol: holding for holding in snapshot.holdings}
    warnings: list[PortfolioWarning] = []

    for symbol, previous in previous_by_symbol.items():
        if symbol not in current_by_symbol and previous.market_value_jpy >= DISAPPEARANCE_VALUE_THRESHOLD_JPY:
            warnings.append(
                PortfolioWarning(
                    code="previous_holding_disappeared",
                    severity="warning",
                    message=(
                        f"{symbol}: existed in previous snapshot at {previous.market_value_jpy} JPY "
                        "but is absent from current snapshot. Confirm sale, merge, rename, or OCR miss."
                    ),
                    related_symbols=[symbol],
                )
            )

    for symbol, current in current_by_symbol.items():
        previous = previous_by_symbol.get(symbol)
        if previous is None:
            continue
        if current.asset_class != previous.asset_class:
            warnings.append(
                PortfolioWarning(
                    code="asset_class_changed_from_previous_snapshot",
                    severity="warning",
                    message=(
                        f"{symbol}: asset_class changed from {previous.asset_class} to {current.asset_class}. "
                        "Confirm this is intentional before investment review."
                    ),
                    related_symbols=[symbol],
                )
            )
        gap = current.market_value_jpy - previous.market_value_jpy
        if is_large_month_over_month_change(gap, previous.market_value_jpy):
            pct_change = gap / previous.market_value_jpy if previous.market_value_jpy else None
            warnings.append(
                PortfolioWarning(
                    code="large_month_over_month_change",
                    severity="warning",
                    message=(
                        f"{symbol}: market_value_jpy changed from {previous.market_value_jpy} to "
                        f"{current.market_value_jpy} (gap={gap}, pct={pct_change}). Verify OCR digits, "
                        "purchases/sales, and account grouping."
                    ),
                    related_symbols=[symbol],
                )
            )
    return warnings


def is_large_month_over_month_change(gap: Decimal, previous_value: Decimal) -> bool:
    if abs(gap) >= MONTH_OVER_MONTH_CHANGE_ABS_THRESHOLD_JPY:
        return True
    if previous_value == 0:
        return False
    return (
        abs(gap) >= DISAPPEARANCE_VALUE_THRESHOLD_JPY
        and abs(gap / previous_value) >= MONTH_OVER_MONTH_CHANGE_PCT_THRESHOLD
    )


def normalize_identity_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).lower().split())


def contains_any(value: str, needles: tuple[str, ...]) -> bool:
    return any(needle.lower() in value.lower() for needle in needles)


def dedupe_warnings(warnings: list[PortfolioWarning]) -> list[PortfolioWarning]:
    deduped: list[PortfolioWarning] = []
    seen: set[tuple[str, str]] = set()
    for warning in warnings:
        key = (warning.code, warning.message)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(warning)
    return deduped
