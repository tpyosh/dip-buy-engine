from __future__ import annotations

from decimal import Decimal

import pandas as pd
import pytest

from monthly_limit_order_review.market_data import MarketDataError, fetch_market_references


def build_history(length: int) -> pd.DataFrame:
    index = pd.date_range("2025-12-01", periods=length, freq="B")
    closes = list(range(100, 100 + length))
    return pd.DataFrame({"Close": closes}, index=index)


def test_market_data_computes_mean_and_recent_high() -> None:
    history = build_history(70)
    references = fetch_market_references(
        {"MSFT": {"yfinance_symbol": "MSFT", "currency": "USD"}},
        history_provider=lambda _: history,
    )

    reference = references[0]
    assert reference.current_price == Decimal("169.0000")
    assert reference.mean_close_20d == Decimal("159.5000")
    assert reference.recent_high_21d == Decimal("169.0000")
    assert reference.recent_high_63d == Decimal("169.0000")


def test_market_data_raises_when_history_is_too_short() -> None:
    history = build_history(30)

    with pytest.raises(MarketDataError):
        fetch_market_references(
            {"MSFT": {"yfinance_symbol": "MSFT", "currency": "USD"}},
            history_provider=lambda _: history,
        )
