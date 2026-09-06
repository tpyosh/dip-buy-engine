from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
import pytest

from monthly_limit_order_review.market_data import (
    MarketDataError,
    fetch_intraday_quote,
    fetch_market_references,
)


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
    assert reference.mean_close_20d == Decimal("154.5000")
    assert reference.mean_close_30d == Decimal("154.5000")
    assert reference.recent_high_21d == Decimal("169.0000")
    assert reference.recent_high_63d == Decimal("169.0000")
    assert reference.prior_close_1d == Decimal("168.0000")
    assert reference.prior_close_5d == Decimal("164.0000")
    assert reference.prior_close_21d == Decimal("148.0000")
    assert reference.prior_close_63d == Decimal("106.0000")


@pytest.mark.parametrize("length", [30, 63])
def test_market_data_raises_when_history_is_too_short(length: int) -> None:
    history = build_history(length)

    with pytest.raises(MarketDataError):
        fetch_market_references(
            {"MSFT": {"yfinance_symbol": "MSFT", "currency": "USD"}},
            history_provider=lambda _: history,
        )


def test_intraday_quote_exposes_timestamp_and_never_claims_live_bid_ask() -> None:
    index = pd.DatetimeIndex(["2026-08-07T15:59:00-04:00"])
    history = pd.DataFrame({"Close": [97.86]}, index=index)

    quote = fetch_intraday_quote(
        "CIBR",
        history_provider=lambda _: history,
        fetched_at=datetime(2026, 8, 10, 4, 24, tzinfo=UTC),
    )

    assert quote["price"] == 97.86
    assert quote["price_kind"] == "latest_available_one_minute_close"
    assert quote["market_timestamp"] == "2026-08-07T15:59:00-04:00"
    assert quote["age_seconds"] > 0
    assert quote["bid"] is None
    assert quote["ask"] is None
    assert quote["is_realtime_quote"] is False
    assert quote["usable_as_broker_bid_ask"] is False
