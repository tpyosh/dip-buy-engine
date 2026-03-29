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
    semiconductor_group = get_exposure_group(policy_config, "direct_semiconductor")
    if not semiconductor_group:
        semiconductor_group = get_exposure_group(policy_config, "semiconductor")
    indirect_group = get_exposure_group(policy_config, "indirect_ai_infra")
    optional_symbols = get_optional_exposure_symbols(semiconductor_group)
    indirect_symbols = {item.upper() for item in indirect_group.get("symbols", [])}
    breakdown: list[dict] = []
    direct_total_jpy = Decimal("0")
    indirect_total_jpy = Decimal("0")

    for holding in snapshot.holdings:
        symbol_upper = holding.symbol.upper()
        matches_group = holding_matches_exposure_group(holding, semiconductor_group)
        is_indirect = symbol_upper in indirect_symbols
        if not matches_group and symbol_upper not in optional_symbols and not is_indirect:
            continue

        include_direct = False
        include_indirect = False
        reason = "matched_exposure_group_rule"
        exposure_type = "direct_semiconductor"
        if matches_group:
            include_direct = True
            reason = "matched_exposure_group_rule"
            exposure_type = "direct_semiconductor"
        elif symbol_upper in optional_symbols:
            include_direct = optional_symbols[symbol_upper]
            reason = "config_optional_included" if include_direct else "config_optional_excluded"
            exposure_type = "config_optional_symbol"
        if is_indirect:
            include_indirect = True
            if not matches_group and symbol_upper not in optional_symbols:
                reason = "matched_indirect_ai_infra_rule"
                exposure_type = "indirect_ai_infra"

        if include_direct:
            direct_total_jpy += holding.market_value_jpy
        if include_indirect:
            indirect_total_jpy += holding.market_value_jpy
        breakdown.append(
            {
                "symbol": holding.symbol,
                "value_jpy": holding.market_value_jpy,
                "bucket": resolved_buckets.get(holding.symbol, holding.asset_class),
                "exposure_type": exposure_type,
                "included_in_semiconductor_exposure": "yes" if include_direct else "no",
                "included_in_direct_semiconductor_exposure": "yes" if include_direct else "no",
                "included_in_indirect_ai_infra_exposure": "yes" if include_indirect else "no",
                "inclusion_reason": reason,
            }
        )

    return {
        "direct_semiconductor_exposure_pct": percent(direct_total_jpy, snapshot.total_assets_jpy),
        "direct_semiconductor_exposure_jpy": direct_total_jpy,
        "indirect_ai_infra_exposure_pct": percent(indirect_total_jpy, snapshot.total_assets_jpy),
        "indirect_ai_infra_exposure_jpy": indirect_total_jpy,
        "semiconductor_exposure_total_pct": percent(direct_total_jpy, snapshot.total_assets_jpy),
        "semiconductor_exposure_total_jpy": direct_total_jpy,
        "breakdown": breakdown,
    }
