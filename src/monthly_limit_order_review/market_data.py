from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

import pandas as pd

from .models import MarketReference
from .utils import quantize


class MarketDataError(RuntimeError):
    """Raised when market data is unavailable or insufficient."""


HistoryProvider = Callable[[str], pd.DataFrame]


@dataclass(slots=True)
class MarketDataFetcher:
    history_provider: HistoryProvider | None = None

    def __post_init__(self) -> None:
        if self.history_provider is None:
            self.history_provider = self._download_history

    def fetch_reference(self, symbol: str, yfinance_symbol: str, currency: str) -> MarketReference:
        history = self.history_provider(yfinance_symbol)
        closes = self._extract_close_series(history)
        if len(closes) < 63:
            raise MarketDataError(
                f"Insufficient trading days for {symbol}: need at least 63 rows, got {len(closes)}"
            )

        as_of = pd.Timestamp(closes.index[-1]).date()
        current_price = quantize(Decimal(str(closes.iloc[-1])), 4)
        mean_close_20d = quantize(Decimal(str(closes.tail(20).mean())), 4)
        recent_high_21d = quantize(Decimal(str(closes.tail(21).max())), 4)
        recent_high_63d = quantize(Decimal(str(closes.tail(63).max())), 4)
        return MarketReference(
            symbol=symbol,
            yfinance_symbol=yfinance_symbol,
            current_price=current_price,
            mean_close_20d=mean_close_20d,
            recent_high_21d=recent_high_21d,
            recent_high_63d=recent_high_63d,
            currency=currency,
            as_of=as_of,
        )

    @staticmethod
    def _download_history(yfinance_symbol: str) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise MarketDataError("yfinance is required to download market data") from exc

        history = yf.download(
            yfinance_symbol,
            period="6mo",
            interval="1d",
            auto_adjust=False,
            progress=False,
        )
        if history.empty:
            raise MarketDataError(f"No market data returned for {yfinance_symbol}")
        return history

    @staticmethod
    def _extract_close_series(history: pd.DataFrame) -> pd.Series:
        if isinstance(history.columns, pd.MultiIndex):
            if "Close" not in history.columns.get_level_values(0):
                raise MarketDataError("Market data is missing Close column")
            close_frame = history["Close"]
            if isinstance(close_frame, pd.DataFrame):
                return close_frame.iloc[:, 0].dropna()
            return close_frame.dropna()

        if "Close" not in history.columns:
            raise MarketDataError("Market data is missing Close column")
        return history["Close"].dropna()


def fetch_market_references(
    requests: dict[str, dict[str, str]],
    *,
    history_provider: HistoryProvider | None = None,
) -> list[MarketReference]:
    fetcher = MarketDataFetcher(history_provider=history_provider)
    references: list[MarketReference] = []
    for symbol, params in requests.items():
        references.append(
            fetcher.fetch_reference(
                symbol=symbol,
                yfinance_symbol=params["yfinance_symbol"],
                currency=params["currency"],
            )
        )
    return references
