from __future__ import annotations

from decimal import Decimal

from .models import Holding, PortfolioSnapshot
from .utils import percent


def get_exposure_group(policy_config: dict, group_name: str) -> dict:
    return policy_config.get("exposure_groups", {}).get(group_name, {})


def holding_matches_exposure_group(holding: Holding, group_config: dict) -> bool:
    symbol = holding.symbol.upper()
    name_upper = holding.name.upper()
    for configured_symbol in group_config.get("symbols", []):
        if symbol == configured_symbol.upper():
            return True
    for prefix in group_config.get("symbol_prefixes", []):
        if symbol.startswith(prefix.upper()):
            return True
    for keyword in group_config.get("name_keywords", []):
        keyword_upper = keyword.upper()
        if keyword_upper in symbol or keyword_upper in name_upper or keyword in holding.name:
            return True
    return False


def get_optional_exposure_symbols(group_config: dict) -> dict[str, bool]:
    return {symbol.upper(): bool(included) for symbol, included in group_config.get("optional_symbols", {}).items()}


def build_exposure_breakdown(
    snapshot: PortfolioSnapshot,
    policy_config: dict,
    resolved_buckets: dict[str, str],
) -> dict:
    semiconductor_group = get_exposure_group(policy_config, "semiconductor")
    optional_symbols = get_optional_exposure_symbols(semiconductor_group)
    breakdown: list[dict] = []
    total_jpy = Decimal("0")

    for holding in snapshot.holdings:
        symbol_upper = holding.symbol.upper()
        matches_group = holding_matches_exposure_group(holding, semiconductor_group)
        if matches_group:
            included = True
            reason = "matched_exposure_group_rule"
            exposure_type = "direct_semiconductor"
        elif symbol_upper in optional_symbols:
            included = optional_symbols[symbol_upper]
            reason = "config_optional_included" if included else "config_optional_excluded"
            exposure_type = "config_optional_symbol"
        else:
            continue

        if included:
            total_jpy += holding.market_value_jpy
        breakdown.append(
            {
                "symbol": holding.symbol,
                "value_jpy": holding.market_value_jpy,
                "bucket": resolved_buckets.get(holding.symbol, holding.asset_class),
                "exposure_type": exposure_type,
                "included_in_semiconductor_exposure": "yes" if included else "no",
                "inclusion_reason": reason,
            }
        )

    return {
        "semiconductor_exposure_total_pct": percent(total_jpy, snapshot.total_assets_jpy),
        "semiconductor_exposure_total_jpy": total_jpy,
        "breakdown": breakdown,
    }
