from __future__ import annotations

from decimal import Decimal

from .models import PortfolioSnapshot

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_long_term_thesis_targets(
    snapshot: PortfolioSnapshot,
    policy_config: dict,
    resolved_buckets: dict[str, str],
    symbol_weights: dict[str, Decimal],
) -> list[dict]:
    thesis_config = policy_config.get("long_term_thesis", {})
    targets: list[dict] = []

    for holding in snapshot.holdings:
        thesis = thesis_config.get(holding.symbol)
        if thesis is None or not thesis.get("enabled", False):
            continue
        targets.append(
            {
                "symbol": holding.symbol,
                "bucket": resolved_buckets.get(holding.symbol, holding.asset_class),
                "current_value_jpy": holding.market_value_jpy,
                "portfolio_pct": symbol_weights.get(holding.symbol, Decimal("0")),
                "thesis_id": thesis.get("thesis_id"),
                "long_term_thesis_summary": thesis.get("long_term_thesis_summary"),
                "key_risk_if_thesis_breaks": thesis.get("key_risk_if_thesis_breaks", []),
                "review_priority": thesis.get("review_priority", "medium"),
                "web_review_required": "yes",
            }
        )

    return sorted(
        targets,
        key=lambda item: (
            PRIORITY_ORDER.get(str(item["review_priority"]).lower(), 99),
            -item["current_value_jpy"],
            item["symbol"],
        ),
    )
