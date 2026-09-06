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
from monthly_limit_order_review.storage import load_yaml, write_yaml

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


def test_generate_review_prompt_writes_only_generated_reports(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_root = tmp_path
    (project_root / "config").mkdir()
    (project_root / "prompts/templates").mkdir(parents=True)
    (project_root / "prompts/generated").mkdir(parents=True)
    (project_root / "plans/recurring/versions").mkdir(parents=True)
    (project_root / "financial/versions").mkdir(parents=True)
    (project_root / "holdings/versions").mkdir(parents=True)
    (project_root / "transactions").mkdir(parents=True)
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
    for path in [
        ROOT / "plans/recurring/current.yaml",
        ROOT / "plans/recurring/versions/2026-03-01.yaml",
        ROOT / "plans/recurring/versions/2026-08-09.yaml",
            ROOT / "financial/current.yaml",
            ROOT / "financial/versions/2026-08-02.yaml",
            ROOT / "financial/versions/2026-08-03.yaml",
            ROOT / "financial/versions/2026-08-03-v2.yaml",
            ROOT / "financial/versions/2026-08-09.yaml",
            ROOT / "financial/versions/2026-08-09-v2.yaml",
            ROOT / "financial/versions/2026-08-10-v3.yaml",
            ROOT / "financial/versions/2026-08-29-v4.yaml",
            ROOT / "holdings/current.yaml",
            ROOT / "holdings/versions/2026-08-09.yaml",
            ROOT / "holdings/versions/2026-08-09-v2.yaml",
            ROOT / "holdings/versions/2026-08-10.yaml",
                ROOT / "holdings/versions/2026-08-10-v2.yaml",
                ROOT / "holdings/versions/2026-08-13-v3.yaml",
                ROOT / "holdings/versions/2026-08-14-v4.yaml",
                ROOT / "transactions/ledger.yaml",
    ]:
        destination = project_root / path.relative_to(ROOT)
        destination.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    (project_root / "prompts/templates/monthly_review_template.md").write_text(
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    snapshot_path = project_root / "snapshot.yaml"
    snapshot_payload = load_yaml(ROOT / "data/normalized/snapshot_2026_04.yaml")
    for holding in snapshot_payload["holdings"]:
        if holding.get("asset_class") in {
            "core",
            "jun_core",
            "satellite_core",
            "satellite",
        }:
            holding["account_type"] = "特定口座（源泉徴収あり）"
    write_yaml(snapshot_path, snapshot_payload)

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
    assert readme_path.read_text(encoding="utf-8") == "# Title\n\n## 目的\nbody\n"
    assert (project_root / "reports/generated/monthly/2026_04/computation.yaml").exists()
    packet_path = project_root / "reports/generated/monthly/2026_04/review_packet.yaml"
    prompt_path = project_root / "reports/generated/monthly/2026_04/review_request.md"
    assert packet_path.exists()
    assert prompt_path.exists()
    packet = load_yaml(packet_path)
    prompt = prompt_path.read_text(encoding="utf-8")
    assert packet["packet_type"] == "on_demand_independent_review"
    assert packet["review_cadence"] == "on_demand"
    assert packet["review_target_month"] == "2026_04"
    assert "# ChatGPT向けオンデマンド包括レビュー" in prompt
    assert "## 1. モードと対話フェーズ" in prompt
    assert "generation_status: ready" in prompt
    assert "active_strategy" not in prompt
    assert "candidate_orders" not in prompt
    assert not (project_root / "docs/portfolio_allocation_latest.svg").exists()


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
