from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.cli import build_reference_requests
from monthly_limit_order_review.portfolio_metrics import compute_portfolio_metrics
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.storage import load_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_build_reference_requests_includes_taxable_all_country_reference() -> None:
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_04.yaml")
    buy_rules = load_yaml(ROOT / "config/buy_rules.yaml")
    tickers = load_yaml(ROOT / "config/tickers.yaml")
    market_reference = load_yaml(ROOT / "config/market_reference.yaml")
    tickers.setdefault("yfinance_symbols", {}).update(market_reference.get("yfinance_symbols", {}))
    portfolio_policy = load_yaml(ROOT / "config/portfolio_policy.yaml")
    analysis = compute_portfolio_metrics(snapshot, portfolio_policy)

    requests = build_reference_requests(snapshot, buy_rules, tickers, analysis["resolved_buckets"])

    assert "EMAXIS_ALL_COUNTRY_TAXABLE" in requests
    assert requests["EMAXIS_ALL_COUNTRY_TAXABLE"]["yfinance_symbol"] == "ACWI"
