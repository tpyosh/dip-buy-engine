from __future__ import annotations

from argparse import Namespace
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from monthly_limit_order_review.cli import (
    build_parser,
    handle_ingest_health_check,
    handle_on_demand_run,
    resolve_on_demand_inventory_path,
)
from monthly_limit_order_review.on_demand import (
    assess_snapshot_freshness,
    build_health_check_window,
    build_on_demand_reference_requests,
    classify_on_demand_holdings,
    enrich_on_demand_market_references,
    render_on_demand_assessment_prompt,
)
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.storage import load_yaml, write_yaml

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
    assert "health_check_response.yaml" in prompt
    assert "schemas/health-check-response.schema.yaml" in prompt
    assert "毎日の連続実行は前提にしない" in prompt
    assert "【投資待機資金の使用判断】" in prompt
    assert "dip_buy_liquidity_deployment_review.use_option" in prompt
    assert "reserve_maintenance_is_objective は false" in prompt
    assert "正式な商品名・会社名" in prompt
    assert "machine_id (Codex YAML only)" in prompt
    assert "account_type_gate_status: complete" in prompt


def test_on_demand_prompt_is_blocked_when_an_account_type_is_missing(
    sample_computation,
) -> None:
    computation = deepcopy(sample_computation)
    computation.snapshot.holdings[1].account_type = None
    freshness = assess_snapshot_freshness(
        computation.snapshot.snapshot_date,
        requested_at=datetime(2026, 3, 7, 9, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="blocked_missing_account_types"):
        render_on_demand_assessment_prompt(
            computation,
            "template",
            inventory_freshness=freshness,
        )


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
        (tmp_path / "reports/generated/on_demand").glob("*/**/health_check_request.md")
    )
    assert not (tmp_path / "data/history/computations").exists()
    assert not (tmp_path / "README.md").exists()


def test_cli_exposes_on_demand_command() -> None:
    args = build_parser().parse_args(["on-demand-run"])

    assert args.func is handle_on_demand_run
    assert args.snapshot is None
    assert args.inventory_max_age_days == 45
    assert args.news_lookback_days == 14

    health_args = build_parser().parse_args(["health-check-run"])
    assert health_args.func is handle_on_demand_run
    assert health_args.max_news_lookback_days == 90

    ingest_args = build_parser().parse_args(
        ["ingest-health-check", "--response-yaml", "response.yaml"]
    )
    assert ingest_args.response_yaml == "response.yaml"
    assert ingest_args.request_dir is None


def test_health_check_window_recovers_gap_without_requiring_daily_runs() -> None:
    window = build_health_check_window(
        requested_at=datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
        base_lookback_days=14,
        last_completed_at=datetime(2026, 7, 25, 8, 0, tzinfo=UTC),
    )

    assert window["status"] == "gap_recovery"
    assert window["effective_lookback_days"] == 28
    assert window["continuous_daily_execution_required"] is False
    assert window["monthly_full_review_is_safety_net"] is True


def test_ingest_health_check_saves_only_validated_complete_response(
    monkeypatch,
    tmp_path: Path,
) -> None:
    request_dir = tmp_path / "reports/generated/on_demand/2026/2026_08_02T120000Z"
    write_yaml(
        request_dir / "market_data.yaml",
        {
            "account_type_gate": {"status": "complete"},
            "security_story_targets": [{"symbol": "MSFT"}],
        },
    )
    response_path = write_yaml(
        tmp_path / "incoming.yaml",
        {
            "schema_version": 1,
            "artifact_type": "portfolio_health_check_response",
            "completed_at": "2026-08-02T12:30:00Z",
            "coverage_start": "2026-07-03",
            "coverage_end": "2026-08-02",
            "human_summary": {"overall_status": "watch", "urgent_items": []},
            "dip_buy_liquidity_deployment_review": {
                "reserve_status": "unknown",
                "market_decline_status": "not_declining",
                "market_evidence": [],
                "use_option": {
                    "considered": False,
                    "status": "not_applicable",
                    "target": None,
                    "amount_jpy": None,
                    "formula": "",
                    "timing": None,
                    "rationale": "下落局面ではない",
                },
                "selected_action": "not_applicable",
                "selection_rationale": "現時点の判定",
                "reserve_maintenance_is_objective": False,
            },
            "security_story_reviews": [
                {
                    "symbol": "MSFT",
                    "evaluated": True,
                    "thesis_status": "inherited_pending_review",
                    "provisional_story": None,
                    "material_facts": [],
                    "story_health": "watch",
                    "invalidation_signals": [],
                    "decision": "hold",
                    "decision_rationale": "一次情報を確認",
                    "next_review_triggers": [],
                    "sources": [],
                }
            ],
            "cross_holding_themes": [],
            "alerts": [],
            "next_check_triggers": [],
            "codex_handoff": {"thesis_updates_proposed": [], "data_gaps": []},
        },
    )
    monkeypatch.setattr("monthly_limit_order_review.cli.get_project_root", lambda: tmp_path)

    result = handle_ingest_health_check(
        Namespace(
            response_yaml=str(response_path),
            request_dir=str(request_dir),
            verbose=False,
        )
    )

    assert result == 0
    saved = load_yaml(request_dir / "health_check_response.yaml")
    assert saved["completed_at"] == "2026-08-02T12:30:00Z"


def test_on_demand_uses_latest_snapshot_as_symbol_inventory_by_default() -> None:
    path = resolve_on_demand_inventory_path(ROOT, None)
    expected = max(
        (ROOT / "data/normalized").glob("snapshot_20??_??.yaml"),
        key=lambda candidate: candidate.stem,
    )

    assert path == expected
