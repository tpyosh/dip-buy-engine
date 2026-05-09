from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml

from .models import Holding, PortfolioSnapshot
from .utils import to_decimal, to_optional_decimal

LOGGER = logging.getLogger(__name__)

ROOT_REQUIRED_FIELDS = ("snapshot_date", "currency_base", "total_assets_jpy", "holdings")
OPTIONAL_HOLDING_FIELDS = ("quantity", "avg_cost", "current_price")
TOTAL_ASSETS_TOLERANCE_JPY = Decimal("10")


def load_snapshot(path: str | Path) -> PortfolioSnapshot:
    snapshot_path = Path(path)
    payload = yaml.safe_load(snapshot_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Snapshot must be a mapping: {snapshot_path}")

    missing_root = [field for field in ROOT_REQUIRED_FIELDS if field not in payload]
    if missing_root:
        raise ValueError(f"Snapshot is missing required fields: {', '.join(missing_root)}")

    warnings: list[str] = []
    holdings_payload = payload.get("holdings")
    if not isinstance(holdings_payload, list):
        raise ValueError("Snapshot field 'holdings' must be a list")

    holdings: list[Holding] = []
    for index, item in enumerate(holdings_payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Holding at index {index} must be a mapping")

        symbol = str(item.get("symbol") or f"UNKNOWN_{index}")
        name = str(item.get("name") or symbol)
        asset_class = str(item.get("asset_class") or "other")
        currency = str(item.get("currency") or "JPY")
        if item.get("symbol") in (None, ""):
            warnings.append(f"Holding #{index} is missing symbol; substituted {symbol}.")
        if item.get("name") in (None, ""):
            warnings.append(f"Holding {symbol} is missing name; using symbol as name.")
        if item.get("asset_class") in (None, ""):
            warnings.append(f"Holding {symbol} is missing asset_class; defaulted to other.")
        if item.get("currency") in (None, ""):
            warnings.append(f"Holding {symbol} is missing currency; defaulted to JPY.")
        if item.get("market_value_jpy") in (None, ""):
            raise ValueError(f"Holding {symbol} is missing required field market_value_jpy")

        for field_name in OPTIONAL_HOLDING_FIELDS:
            if item.get(field_name) in (None, ""):
                warnings.append(f"Holding {symbol} is missing {field_name}; stored as null.")

        holding = Holding(
            symbol=symbol,
            name=name,
            asset_class=asset_class,
            quantity=to_optional_decimal(item.get("quantity")),
            avg_cost=to_optional_decimal(item.get("avg_cost")),
            current_price=to_optional_decimal(item.get("current_price")),
            market_value_jpy=to_decimal(item.get("market_value_jpy"), field_name=f"{symbol}.market_value_jpy"),
            currency=currency,
            source_category=optional_string(item.get("source_category")),
            institution=optional_string(item.get("institution")),
            account_type=optional_string(item.get("account_type")),
            unit_price=to_optional_decimal(item.get("unit_price")),
            profit_loss_jpy=to_optional_decimal(item.get("profit_loss_jpy")),
            valuation_jpy=to_optional_decimal(item.get("valuation_jpy")),
            notes=optional_string(item.get("notes")),
        )
        holdings.append(holding)

    snapshot = PortfolioSnapshot(
        snapshot_date=date.fromisoformat(str(payload["snapshot_date"])),
        currency_base=str(payload["currency_base"]),
        total_assets_jpy=to_decimal(payload["total_assets_jpy"], field_name="total_assets_jpy"),
        liquidity_target_jpy=to_optional_decimal(payload.get("liquidity_target_jpy")),
        holdings=holdings,
        warnings=warnings,
        source_evidence=payload.get("source_evidence") or {},
        category_totals_jpy=load_category_totals(payload),
        ocr_notes=load_string_list(payload.get("ocr_notes")),
        validation_notes=load_string_list(payload.get("validation_notes")),
    )

    holdings_total = sum((holding.market_value_jpy for holding in holdings), start=Decimal("0"))
    if abs(holdings_total - snapshot.total_assets_jpy) > TOTAL_ASSETS_TOLERANCE_JPY:
        message = (
            "Sum of holding market values does not match total_assets_jpy: "
            f"{holdings_total} vs {snapshot.total_assets_jpy}"
        )
        warnings.append(message)
        LOGGER.warning(message)

    return snapshot


def optional_string(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value)


def load_string_list(value) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        return [str(value)]
    return [str(item) for item in value]


def load_category_totals(payload: dict) -> dict[str, Decimal]:
    raw_totals = payload.get("category_totals_jpy") or payload.get("asset_class_totals_jpy") or {}
    if not isinstance(raw_totals, dict):
        raise ValueError("Snapshot field 'category_totals_jpy' must be a mapping when present")
    return {
        str(category): to_decimal(value, field_name=f"category_totals_jpy.{category}")
        for category, value in raw_totals.items()
        if value not in (None, "")
    }
