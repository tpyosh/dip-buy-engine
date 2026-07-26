from __future__ import annotations

from argparse import Namespace
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path

from monthly_limit_order_review.cli import (
    build_parser,
    handle_on_demand_run,
    resolve_on_demand_inventory_path,
)
from monthly_limit_order_review.on_demand import (
    assess_snapshot_freshness,
    build_on_demand_reference_requests,
    classify_on_demand_holdings,
    enrich_on_demand_market_references,
    render_on_demand_assessment_prompt,
)
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.storage import load_yaml

ROOT = Path(__file__).resolve().parents[1]


def test_on_demand_inventory_age_is_labeled_but_does_not_block_market_fetch() -> None:
    requested_at = datetime(2026, 7, 14, 8, 30, tzinfo=UTC)
    freshness = assess_snapshot_freshness(
        date(2026, 7, 14),
        requested_at=requested_at,
        max_age_days=1,
    )

    assert freshness["status"] == "fresh"
    assert freshness["age_days"] == 0

    inventory = assess_snapshot_freshness(
        date(2026, 7, 10),
        requested_at=requested_at,
        max_age_days=1,
    )
    assert inventory["status"] == "stale"
    assert inventory["age_days"] == 4


def test_on_demand_freshness_uses_tokyo_calendar_date() -> None:
    freshness = assess_snapshot_freshness(
        date(2026, 7, 14),
        requested_at=datetime(2026, 7, 13, 23, 30, tzinfo=UTC),
        max_age_days=0,
    )

    assert freshness["status"] == "fresh"
    assert freshness["age_days"] == 0
    assert freshness["requested_at_local"].startswith("2026-07-14T08:30:00+09:00")


def test_on_demand_classification_separates_stocks_funds_and_pension() -> None:
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_07.yaml")

    groups = classify_on_demand_holdings(snapshot)

    assert "7203" in {holding.symbol for holding in groups["stocks"]}
    assert "EMAXIS_SLIM_ALL_COUNTRY" in {
        holding.symbol for holding in groups["investment_funds"]
    }
    assert "PENSION_EMAXIS_SLIM_ALL_COUNTRY" in {
        holding.symbol for holding in groups["pension"]
    }
    assert "LIQUIDITY" in {holding.symbol for holding in groups["context_only"]}


def test_on_demand_reference_requests_cover_current_three_scopes() -> None:
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_07.yaml")
    tickers = load_yaml(ROOT / "config/tickers.yaml")

    requests, missing = build_on_demand_reference_requests(snapshot, tickers)

    assert requests["7203"]["yfinance_symbol"] == "7203.T"
    assert requests["7203"]["currency"] == "JPY"
    assert requests["NISSEI_SOX_1"]["yfinance_symbol"] == "SOXX"
    assert requests["PENSION_EMAXIS_SLIM_ALL_COUNTRY"]["yfinance_symbol"] == "ACWI"
    assert missing == []


def test_on_demand_market_collection_keeps_individual_fetch_failure_as_warning(
    sample_computation,
) -> None:
    computation = deepcopy(sample_computation)

    def fail_reference(symbol: str, yfinance_symbol: str, currency: str):
        raise RuntimeError("temporary provider error")

    result = enrich_on_demand_market_references(
        computation,
        {"yfinance_symbols": {"NIKKO_SOX_FUND": "SOXX"}},
        reference_fetcher=fail_reference,
    )

    assert result["failed_symbols"] == {"NIKKO_SOX_FUND": "temporary provider error"}
    assert any(
        warning.code == "on_demand_market_reference_fetch_failed"
        and warning.related_symbols == ["NIKKO_SOX_FUND"]
        for warning in computation.warnings
    )


def test_on_demand_prompt_focuses_on_price_moves_and_news_not_portfolio_status(sample_computation) -> None:
    template = (ROOT / "prompts/templates/on_demand_assessment_template.md").read_text(encoding="utf-8")
    freshness = assess_snapshot_freshness(
        sample_computation.snapshot.snapshot_date,
        requested_at=datetime(2026, 3, 7, 9, 0, tzinfo=UTC),
    )

    prompt = render_on_demand_assessment_prompt(
        sample_computation,
        template,
        inventory_freshness=freshness,
        news_lookback_days=10,
    )

    assert "【調査時点と市場概況】" in prompt
    assert "【銘柄別アセスメント】" in prompt
    assert "【横断テーマ】" in prompt
    assert "因果関係の確度" in prompt
    assert "Reuters" in prompt
    assert "## 3. 株式" in prompt
    assert "## 4. 投資信託" in prompt
    assert "## 5. 年金" in prompt
    assert "holdings_inventory_usage: 銘柄名の特定だけに使用" in prompt
    assert "authoritative_news_lookback_days: 10" in prompt
    assert "intraday real-time quote is not guaranteed" in prompt
    assert "return_1d_pct" in prompt
    assert "return_5d_pct" in prompt
    assert "| MSFT | Microsoft |" in prompt
    assert "| ALL_COUNTRY_FUND | All Country Mutual Funds |" in prompt
    assert "total_assets_jpy" not in prompt
    assert "value_jpy" not in prompt
    assert "profit_loss_jpy" not in prompt
    assert "avg_cost" not in prompt
    assert "【Codex向け修正要約】" not in prompt


def test_on_demand_run_writes_separate_history_without_monthly_side_effects(
    monkeypatch,
    tmp_path: Path,
    sample_computation,
    sample_snapshot_path: Path,
) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "prompts/templates").mkdir(parents=True)
    (tmp_path / "config/tickers.yaml").write_text("yfinance_symbols: {}\n", encoding="utf-8")
    (tmp_path / "prompts/templates/on_demand_assessment_template.md").write_text(
        (ROOT / "prompts/templates/on_demand_assessment_template.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    output_path = tmp_path / "result.md"

    monkeypatch.setattr("monthly_limit_order_review.cli.get_project_root", lambda: tmp_path)
    monkeypatch.setattr(
        "monthly_limit_order_review.cli.compute_on_demand",
        lambda snapshot_path, *, project_root, requested_at: deepcopy(sample_computation),
    )
    monkeypatch.setattr(
        "monthly_limit_order_review.cli.enrich_on_demand_market_references",
        lambda computation, tickers: {
            "requested_symbols": [],
            "already_available_symbols": [],
            "fetched_symbols": [],
            "missing_mapping_symbols": [],
            "failed_symbols": {},
        },
    )

    result = handle_on_demand_run(
        Namespace(
            snapshot=str(sample_snapshot_path),
            output=str(output_path),
            inventory_max_age_days=45,
            news_lookback_days=14,
            verbose=False,
        )
    )

    assert result == 0
    assert output_path.exists()
    market_data_paths = list(
        (tmp_path / "reports/generated/on_demand").glob("*/**/market_data.yaml")
    )
    assert market_data_paths
    market_data = load_yaml(market_data_paths[0])
    serialized = str(market_data)
    assert "total_assets_jpy" not in serialized
    assert "market_value_jpy" not in serialized
    assert "profit_loss_jpy" not in serialized
    assert "avg_cost" not in serialized
    assert "quantity" not in serialized
    assert list(
        (tmp_path / "reports/generated/on_demand").glob("*/**/assessment_request.md")
    )
    assert not (tmp_path / "data/history/computations").exists()
    assert not (tmp_path / "README.md").exists()


def test_cli_exposes_on_demand_command() -> None:
    args = build_parser().parse_args(["on-demand-run"])

    assert args.func is handle_on_demand_run
    assert args.snapshot is None
    assert args.inventory_max_age_days == 45
    assert args.news_lookback_days == 14


def test_on_demand_uses_latest_snapshot_as_symbol_inventory_by_default() -> None:
    path = resolve_on_demand_inventory_path(ROOT, None)

    assert path.name == "snapshot_2026_07.yaml"
