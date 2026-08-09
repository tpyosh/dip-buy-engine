from __future__ import annotations

from .models import PortfolioSnapshot


REVIEW_ACCOUNT_CATEGORIES = ("NISA", "特定口座", "一般口座")
REVIEW_TRADABLE_ASSET_CLASSES = {
    "core",
    "jun_core",
    "satellite_core",
    "satellite",
}


def classify_review_account_type(account_type: str | None) -> str | None:
    """Map a confirmed display value to the account categories required for review."""
    if account_type is None:
        return None
    normalized = str(account_type).strip()
    if not normalized:
        return None
    if "NISA" in normalized.upper():
        return "NISA"
    if "特定口座" in normalized:
        return "特定口座"
    if "一般口座" in normalized:
        return "一般口座"
    return None


def build_account_type_gate(snapshot: PortfolioSnapshot) -> dict:
    checked = []
    missing = []
    for holding in snapshot.holdings:
        if holding.asset_class not in REVIEW_TRADABLE_ASSET_CLASSES:
            continue
        category = classify_review_account_type(holding.account_type)
        item = {
            "symbol": holding.symbol,
            "name": holding.name,
            "account_type": holding.account_type,
            "account_category": category,
        }
        checked.append(item)
        if category is None:
            missing.append(
                {
                    "symbol": holding.symbol,
                    "name": holding.name,
                    "observed_account_type": holding.account_type,
                }
            )

    return {
        "status": "complete" if not missing else "blocked",
        "required_account_categories": list(REVIEW_ACCOUNT_CATEGORIES),
        "checked_holding_count": len(checked),
        "checked_holdings": checked,
        "missing_or_unclassified_holdings": missing,
        "generation_rule": (
            "NISA・特定口座・一般口座のいずれかが全売買可能明細で確認できるまで、"
            "ChatGPT向けレビュー依頼とレビュー出力を生成しない"
        ),
    }


def require_complete_account_type_gate(snapshot: PortfolioSnapshot) -> dict:
    gate = build_account_type_gate(snapshot)
    if gate["status"] == "complete":
        return gate
    missing = ", ".join(
        item["symbol"] for item in gate["missing_or_unclassified_holdings"]
    )
    raise ValueError(
        "blocked_missing_account_types: "
        + missing
        + ". Confirm each holding as NISA, 特定口座, or 一般口座 before generating review output."
    )
