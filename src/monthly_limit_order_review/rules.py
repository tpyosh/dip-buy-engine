from __future__ import annotations

from decimal import Decimal

from .models import CandidateOrder, MarketReference, PortfolioSnapshot
from .utils import quantize, to_decimal, to_optional_decimal


def calculate_candidate_orders(
    snapshot: PortfolioSnapshot,
    buy_rules_config: dict,
    portfolio_policy: dict,
    market_references: list[MarketReference],
    *,
    liquidity_jpy: Decimal,
    symbol_weights: dict[str, Decimal],
) -> list[CandidateOrder]:
    reference_map = {reference.symbol: reference for reference in market_references}
    hard_floor = to_decimal(
        portfolio_policy.get("cash_policy", {}).get("hard_floor_jpy", 0),
        field_name="cash_policy.hard_floor_jpy",
    )
    round_rules = buy_rules_config.get("execution", {}).get("round_price", {})
    pltr_limit = to_optional_decimal(
        portfolio_policy.get("risk_limits", {}).get("pltr_max_total_assets_pct")
    ) or Decimal("0")
    usd_jpy = reference_map.get("USDJPY")

    spent_jpy = Decimal("0")
    candidates: list[CandidateOrder] = []

    for symbol, rule_config in buy_rules_config.get("limit_order_rules", {}).items():
        if symbol not in reference_map:
            raise ValueError(f"Missing market reference for candidate symbol {symbol}")
        reference = reference_map[symbol]
        if reference.mean_close_20d is None:
            raise ValueError(f"Base price is unavailable for {symbol}")

        digits = int(round_rules.get("jpy_decimals" if reference.currency == "JPY" else "usd_decimals", 2))
        base_price = reference.mean_close_20d
        current_price = reference.current_price

        for tranche in rule_config.get("tranches", []):
            drawdown_pct = to_decimal(tranche["drawdown_pct"], field_name=f"{symbol}.drawdown_pct")
            shares = int(tranche["shares"])
            limit_price = quantize(
                base_price * (Decimal("1") + (drawdown_pct / Decimal("100"))),
                digits,
            )
            estimated_cost = quantize(limit_price * Decimal(shares), digits)
            estimated_cost_jpy = _estimate_cost_jpy(estimated_cost, reference.currency, usd_jpy)

            suppression_reasons: list[str] = []
            if estimated_cost_jpy is not None and (liquidity_jpy - spent_jpy - estimated_cost_jpy) < hard_floor:
                suppression_reasons.append("Liquidity hard floor would be breached.")

            if symbol == "PLTR" and symbol_weights.get("PLTR", Decimal("0")) > pltr_limit and drawdown_pct > Decimal(
                "-15"
            ):
                suppression_reasons.append("PLTR already exceeds policy cap; shallow dip tranche is suppressed.")

            suppressed = bool(suppression_reasons)
            if not suppressed and estimated_cost_jpy is not None:
                spent_jpy += estimated_cost_jpy

            candidates.append(
                CandidateOrder(
                    symbol=symbol,
                    base_price=base_price,
                    current_price=current_price,
                    limit_price=limit_price,
                    shares=shares,
                    estimated_cost=estimated_cost,
                    estimated_cost_jpy=estimated_cost_jpy,
                    currency=reference.currency,
                    drawdown_pct=drawdown_pct,
                    reference_method="mean_close_20d",
                    suppressed=suppressed,
                    suppression_reasons=suppression_reasons,
                )
            )

    return candidates


def calculate_sox_buy_signal(
    buy_rules_config: dict,
    market_references: list[MarketReference],
) -> dict:
    reference_map = {reference.symbol: reference for reference in market_references}
    sox_config = buy_rules_config.get("sox_buy_judgement", {})
    proxy_symbol = sox_config.get("proxy_symbol")
    if proxy_symbol not in reference_map:
        raise ValueError(f"Missing market reference for SOX proxy {proxy_symbol}")

    proxy_reference = reference_map[proxy_symbol]
    if proxy_reference.recent_high_63d in (None, Decimal("0")):
        raise ValueError("SOX proxy recent_high_63d is unavailable")

    current_price = to_decimal(proxy_reference.current_price, field_name=f"{proxy_symbol}.current_price")
    recent_high_63d = to_decimal(
        proxy_reference.recent_high_63d,
        field_name=f"{proxy_symbol}.recent_high_63d",
    )
    drawdown_pct = quantize(
        ((current_price - recent_high_63d) / recent_high_63d) * Decimal("100"),
        2,
    )
    buy_zone_min = to_decimal(sox_config["buy_zone_min_pct"], field_name="sox_buy_judgement.buy_zone_min_pct")
    buy_zone_max = to_decimal(sox_config["buy_zone_max_pct"], field_name="sox_buy_judgement.buy_zone_max_pct")
    within_buy_zone = buy_zone_min <= drawdown_pct <= buy_zone_max

    return {
        "proxy_symbol": proxy_symbol,
        "method": sox_config.get("method"),
        "current_price": current_price,
        "recent_high_63d": recent_high_63d,
        "drawdown_pct": drawdown_pct,
        "buy_zone_min_pct": buy_zone_min,
        "buy_zone_max_pct": buy_zone_max,
        "within_buy_zone": within_buy_zone,
        "monthly_buy_budget_jpy": sox_config.get("monthly_buy_budget_jpy", {}),
    }


def _estimate_cost_jpy(
    estimated_cost: Decimal,
    currency: str,
    usd_jpy_reference: MarketReference | None,
) -> Decimal | None:
    if currency == "JPY":
        return quantize(estimated_cost, 0)
    if currency == "USD" and usd_jpy_reference is not None:
        return quantize(estimated_cost * usd_jpy_reference.current_price, 0)
    return None
