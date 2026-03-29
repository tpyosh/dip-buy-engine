from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
from typing import Any


def to_decimal(value: Any, *, field_name: str) -> Decimal:
    if value is None:
        raise ValueError(f"{field_name} must not be null")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def to_optional_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize(value: Decimal, digits: int) -> Decimal:
    quantum = Decimal("1") if digits == 0 else Decimal("1").scaleb(-digits)
    return value.quantize(quantum, rounding=ROUND_HALF_UP)


def percent(numerator: Decimal, denominator: Decimal, *, digits: int = 4) -> Decimal:
    if denominator == 0:
        raise ZeroDivisionError("denominator must not be zero")
    raw = numerator / denominator
    return quantize(raw, digits)


def month_key(snapshot_date: date) -> str:
    return snapshot_date.strftime("%Y_%m")


def infer_target_month_start(snapshot_date: date, *, snapshot_path: str | Path | None = None) -> date:
    if snapshot_path is not None:
        match = re.search(r"snapshot_(\d{4})_(\d{2})\.ya?ml$", str(snapshot_path))
        if match:
            return date(int(match.group(1)), int(match.group(2)), 1)
    if snapshot_date.day >= 25:
        year = snapshot_date.year + (1 if snapshot_date.month == 12 else 0)
        month = 1 if snapshot_date.month == 12 else snapshot_date.month + 1
        return date(year, month, 1)
    return date(snapshot_date.year, snapshot_date.month, 1)


def target_month_key(snapshot_date: date, *, snapshot_path: str | Path | None = None) -> str:
    return infer_target_month_start(snapshot_date, snapshot_path=snapshot_path).strftime("%Y_%m")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def to_serializable(value: Any) -> Any:
    if is_dataclass(value):
        return to_serializable(asdict(value))
    if isinstance(value, dict):
        return {key: to_serializable(val) for key, val in value.items()}
    if isinstance(value, list):
        return [to_serializable(item) for item in value]
    if isinstance(value, tuple):
        return [to_serializable(item) for item in value]
    if isinstance(value, Decimal):
        if value == value.to_integral():
            return int(value)
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
