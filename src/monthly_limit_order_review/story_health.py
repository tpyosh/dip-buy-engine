from __future__ import annotations

from .models import PortfolioSnapshot


DEFAULT_ETF_SYMBOLS = {"CIBR", "SMH", "URA"}


def build_security_story_targets(
    snapshot: PortfolioSnapshot,
    thesis_policy: dict[str, dict],
    holding_metadata: dict[str, dict] | None = None,
) -> list[dict]:
    """Build a review target for every directly held stock or ETF.

    Missing thesis records are deliberately retained as review targets.  This
    prevents the prompt from silently skipping a holding merely because the
    repository does not yet contain a documented investment story for it.
    """

    targets: list[dict] = []
    metadata_by_symbol = holding_metadata or {}
    for holding in snapshot.holdings:
        if not _is_direct_security(holding.source_category):
            continue
        thesis = thesis_policy.get(holding.symbol, {})
        thesis_recorded = bool(thesis)
        instrument_type = thesis.get("instrument_type") or (
            "etf" if holding.symbol in DEFAULT_ETF_SYMBOLS else "individual_stock"
        )
        metadata = metadata_by_symbol.get(holding.symbol, {})
        user_intent = metadata.get("user_intent", {})
        execution_status = metadata.get("execution_status", {})
        targets.append(
            {
                "symbol": holding.symbol,
                "name": holding.name,
                "instrument_type": instrument_type,
                "thesis_recorded": thesis_recorded,
                "thesis_id": thesis.get("thesis_id"),
                "thesis_status": thesis.get("thesis_status") if thesis_recorded else "missing",
                "thesis_summary": thesis.get("long_term_thesis_summary"),
                "invalidation_conditions": list(
                    thesis.get("key_risk_if_thesis_breaks", [])
                ),
                "review_priority": thesis.get("review_priority", "high" if not thesis_recorded else "medium"),
                "thesis_source_ref": thesis.get("thesis_source_ref"),
                "user_holding_reason": user_intent.get("holding_reason"),
                "user_disposition": user_intent.get("disposition"),
                "user_sell_condition": user_intent.get("sell_condition"),
                "holding_metadata_confirmed_at": user_intent.get("confirmed_at"),
                "sell_order_available": execution_status.get(
                    "sell_order_available"
                ),
                "unreflected_orders": execution_status.get("unreflected_orders"),
                "planned_withdrawals": execution_status.get("planned_withdrawals"),
                "restricted_funds": execution_status.get("restricted_funds"),
                "required_assessment": (
                    "既存仮説を最新の一次情報と照合し、健全性と売買判断を記録する"
                    if thesis_recorded
                    else (
                        "ユーザの現在の保有意図を制約として、最新の一次情報から暫定ストーリーを再構成し、売買判断を示す"
                        if user_intent.get("holding_reason")
                        else "保有理由が未記録。最新の一次情報から暫定ストーリーを再構成し、ユーザ確認事項を明示する"
                    )
                ),
            }
        )
    return sorted(
        targets,
        key=lambda item: (
            0 if not item["thesis_recorded"] else 1,
            item["instrument_type"],
            item["symbol"],
        ),
    )


def _is_direct_security(source_category: str | None) -> bool:
    return "株式" in (source_category or "")
