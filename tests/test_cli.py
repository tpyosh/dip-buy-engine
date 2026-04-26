from __future__ import annotations

from argparse import Namespace
from datetime import date
from decimal import Decimal
from pathlib import Path

from monthly_limit_order_review.cli import (
    build_reference_requests,
    estimate_cash_normalization_months,
    handle_generate_review_prompt,
)
from monthly_limit_order_review.models import BucketAllocation, MarketReference
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


def test_build_reference_requests_includes_2026_05_core_proxies() -> None:
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_05.yaml")
    buy_rules = load_yaml(ROOT / "config/buy_rules.yaml")
    tickers = load_yaml(ROOT / "config/tickers.yaml")
    market_reference = load_yaml(ROOT / "config/market_reference.yaml")
    tickers.setdefault("yfinance_symbols", {}).update(market_reference.get("yfinance_symbols", {}))
    portfolio_policy = load_yaml(ROOT / "config/portfolio_policy.yaml")
    analysis = compute_portfolio_metrics(snapshot, portfolio_policy)

    requests = build_reference_requests(snapshot, buy_rules, tickers, analysis["resolved_buckets"])

    assert requests["EMAXIS_SLIM_ALL_COUNTRY"]["yfinance_symbol"] == "ACWI"
    assert requests["EMAXIS_SLIM_SP500_1"]["yfinance_symbol"] == "VOO"
    assert requests["EMAXIS_SLIM_SP500_2"]["yfinance_symbol"] == "VOO"
    assert requests["EMAXIS_SLIM_SP500_3"]["yfinance_symbol"] == "VOO"
    assert requests["RAKUTEN_PLUS_ALL_COUNTRY_1"]["yfinance_symbol"] == "VT"
    assert requests["RAKUTEN_PLUS_ALL_COUNTRY_2"]["yfinance_symbol"] == "VT"
    assert requests["RAKUTEN_PLUS_SP500"]["yfinance_symbol"] == "VOO"


def test_generate_review_prompt_updates_readme(monkeypatch, tmp_path: Path) -> None:
    project_root = tmp_path
    (project_root / "config").mkdir()
    (project_root / "prompts/templates").mkdir(parents=True)
    (project_root / "prompts/generated").mkdir(parents=True)
    (project_root / "data/history/prompts").mkdir(parents=True)
    (project_root / "data/history/computations").mkdir(parents=True)
    readme_path = project_root / "README.md"
    readme_path.write_text("# Title\n\n## 目的\nbody\n", encoding="utf-8")

    for path in [
        ROOT / "config/buy_rules.yaml",
        ROOT / "config/portfolio_policy.yaml",
        ROOT / "config/tickers.yaml",
        ROOT / "config/allocation_rules.yaml",
        ROOT / "config/market_reference.yaml",
        ROOT / "config/classification_overrides.yaml",
        ROOT / "config/core_recurring_contributions.yaml",
    ]:
        (project_root / "config" / path.name).write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (project_root / "prompts/templates/monthly_review_template.md").write_text(
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    snapshot_path = project_root / "snapshot.yaml"
    snapshot_path.write_text((ROOT / "data/normalized/snapshot_2026_04.yaml").read_text(encoding="utf-8"), encoding="utf-8")

    def fake_references(requests: dict[str, dict[str, str]]) -> list[MarketReference]:
        references: list[MarketReference] = []
        for symbol, params in requests.items():
            references.append(
                MarketReference(
                    symbol=symbol,
                    yfinance_symbol=params["yfinance_symbol"],
                    current_price=Decimal("100"),
                    mean_close_20d=Decimal("100"),
                    recent_high_21d=Decimal("110"),
                    recent_high_63d=Decimal("120"),
                    currency=params["currency"],
                    as_of=date(2026, 3, 29),
                    prior_close_21d=Decimal("105"),
                    prior_close_63d=Decimal("115"),
                )
            )
        return references

    monkeypatch.setattr("monthly_limit_order_review.cli.get_project_root", lambda: project_root)
    monkeypatch.setattr("monthly_limit_order_review.cli.fetch_market_references", fake_references)

    result = handle_generate_review_prompt(Namespace(snapshot=str(snapshot_path), output=None, verbose=False))

    assert result == 0
    updated_readme = readme_path.read_text(encoding="utf-8")
    assert "<!-- portfolio-piechart:start -->" in updated_readme
    assert "## Latest Portfolio Snapshot" in updated_readme
    assert "snapshot_date: 2026-03-29" in updated_readme
    assert (project_root / "data/history/computations/2026_04_computation.yaml").exists()
    assert (project_root / "data/history/prompts/2026_04_monthly_review_prompt.md").exists()


def test_cash_normalization_estimate_separates_gross_and_net_reduction() -> None:
    liquidity_allocation = BucketAllocation(
        bucket="liquidity",
        market_value_jpy=Decimal("3000000"),
        actual_pct=Decimal("0.30"),
        target_pct=Decimal("0.10"),
        delta_pct=Decimal("0.20"),
        preferred_min_pct=Decimal("0.05"),
        preferred_max_pct=Decimal("0.15"),
    )

    estimate = estimate_cash_normalization_months(
        liquidity_allocation=liquidity_allocation,
        total_assets_jpy=Decimal("10000000"),
        monthly_total_core_deployment_jpy=1450000,
        monthly_cash_inflow_jpy=Decimal("650000"),
    )

    assert estimate["assumed_monthly_cash_inflow_jpy"] == Decimal("650000")
    assert estimate["net_cash_reduction_jpy"] == Decimal("800000")
    assert estimate["gross_deployment_months"] == Decimal("1.4")
    assert estimate["net_cash_reduction_months"] == Decimal("2.5")
