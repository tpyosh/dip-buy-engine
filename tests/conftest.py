from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from monthly_limit_order_review.models import MarketReference, MonthlyComputation
from monthly_limit_order_review.candidate_metrics import compute_candidate_metrics
from monthly_limit_order_review.exposure_metrics import build_exposure_breakdown
from monthly_limit_order_review.portfolio_metrics import build_core_buy_materials, compute_portfolio_metrics
from monthly_limit_order_review.rules import calculate_sox_buy_signal
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.storage import load_yaml
from monthly_limit_order_review.thesis_metrics import build_long_term_thesis_targets
from monthly_limit_order_review.validation import (
    apply_candidate_validations,
    build_exposure_validation_warnings,
    build_validation_warnings,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def buy_rules_config() -> dict:
    buy_rules = load_yaml(ROOT / "config/buy_rules.yaml")
    allocation_rules = load_yaml(ROOT / "config/allocation_rules.yaml")
    if "core_budget_policy" in allocation_rules:
        buy_rules["core_budget_policy"] = allocation_rules["core_budget_policy"]
    return buy_rules


@pytest.fixture
def portfolio_policy_config() -> dict:
    return load_yaml(ROOT / "config/portfolio_policy.yaml")


@pytest.fixture
def sample_snapshot_path(tmp_path: Path) -> Path:
    path = tmp_path / "snapshot.yaml"
    path.write_text(
        """snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 5000000
liquidity_target_jpy: 1000000

holdings:
  - symbol: "JPY_CASH"
    name: "Cash"
    asset_class: "liquidity"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 1200000
    currency: "JPY"

  - symbol: "ALL_COUNTRY_FUND"
    name: "All Country Mutual Funds"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 1800000
    currency: "JPY"

  - symbol: "MSFT"
    name: "Microsoft"
    asset_class: "jun_core"
    quantity: 4
    avg_cost: 410
    current_price: 400
    market_value_jpy: 800000
    currency: "USD"

  - symbol: "NIKKO_SOX_FUND"
    name: "Nikkei SOX Index Fund"
    asset_class: "satellite_core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 600000
    currency: "JPY"

  - symbol: "SMH"
    name: "VanEck Semiconductor ETF"
    asset_class: "satellite_core"
    quantity: 1
    avg_cost: 200
    current_price: 230
    market_value_jpy: 200000
    currency: "USD"

  - symbol: "PLTR"
    name: "Palantir Technologies"
    asset_class: "satellite"
    quantity: 10
    avg_cost: 80
    current_price: 70
    market_value_jpy: 400000
    currency: "USD"
""",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def sample_snapshot(sample_snapshot_path: Path):
    return load_snapshot(sample_snapshot_path)


@pytest.fixture
def sample_market_references() -> list[MarketReference]:
    return [
        MarketReference(
            symbol="CIBR",
            yfinance_symbol="CIBR",
            current_price=Decimal("90"),
            mean_close_20d=Decimal("100"),
            recent_high_21d=Decimal("110"),
            recent_high_63d=Decimal("120"),
            currency="USD",
            as_of=date(2026, 3, 7),
        ),
        MarketReference(
            symbol="URA",
            yfinance_symbol="URA",
            current_price=Decimal("80"),
            mean_close_20d=Decimal("100"),
            recent_high_21d=Decimal("105"),
            recent_high_63d=Decimal("120"),
            currency="USD",
            as_of=date(2026, 3, 7),
        ),
        MarketReference(
            symbol="PLTR",
            yfinance_symbol="PLTR",
            current_price=Decimal("70"),
            mean_close_20d=Decimal("100"),
            recent_high_21d=Decimal("95"),
            recent_high_63d=Decimal("120"),
            currency="USD",
            as_of=date(2026, 3, 7),
        ),
        MarketReference(
            symbol="MSFT",
            yfinance_symbol="MSFT",
            current_price=Decimal("400"),
            mean_close_20d=Decimal("500"),
            recent_high_21d=Decimal("520"),
            recent_high_63d=Decimal("550"),
            currency="USD",
            as_of=date(2026, 3, 7),
        ),
        MarketReference(
            symbol="ALL_COUNTRY_FUND",
            yfinance_symbol="VT",
            current_price=Decimal("105"),
            mean_close_20d=Decimal("100"),
            recent_high_21d=Decimal("110"),
            recent_high_63d=Decimal("120"),
            currency="USD",
            as_of=date(2026, 3, 7),
        ),
        MarketReference(
            symbol="SMH",
            yfinance_symbol="SMH",
            current_price=Decimal("230"),
            mean_close_20d=Decimal("240"),
            recent_high_21d=Decimal("240"),
            recent_high_63d=Decimal("250"),
            currency="USD",
            as_of=date(2026, 3, 7),
        ),
        MarketReference(
            symbol="USDJPY",
            yfinance_symbol="USDJPY=X",
            current_price=Decimal("150"),
            mean_close_20d=Decimal("150"),
            recent_high_21d=Decimal("151"),
            recent_high_63d=Decimal("151"),
            currency="JPY",
            as_of=date(2026, 3, 7),
        ),
    ]


@pytest.fixture
def sample_portfolio_analysis(sample_snapshot, portfolio_policy_config) -> dict:
    return compute_portfolio_metrics(sample_snapshot, portfolio_policy_config)


@pytest.fixture
def sample_exposure_breakdown(sample_snapshot, portfolio_policy_config, sample_portfolio_analysis) -> dict:
    return build_exposure_breakdown(
        sample_snapshot,
        portfolio_policy_config,
        sample_portfolio_analysis["resolved_buckets"],
    )


@pytest.fixture
def sample_candidate_orders(
    sample_snapshot,
    buy_rules_config,
    portfolio_policy_config,
    sample_market_references,
    sample_portfolio_analysis,
):
    raw_candidates = compute_candidate_metrics(
        sample_snapshot,
        buy_rules_config,
        portfolio_policy_config,
        sample_market_references,
        sample_portfolio_analysis["resolved_buckets"],
        sample_portfolio_analysis["bucket_allocations"],
    )
    validated_candidates, _ = apply_candidate_validations(raw_candidates, buy_rules_config)
    return validated_candidates


@pytest.fixture
def sample_core_buy_materials(
    sample_snapshot,
    sample_portfolio_analysis,
    sample_market_references,
    buy_rules_config,
):
    return build_core_buy_materials(
        sample_snapshot,
        sample_portfolio_analysis["bucket_allocations"],
        sample_portfolio_analysis["resolved_buckets"],
        sample_market_references,
        buy_rules_config,
    )


@pytest.fixture
def sample_long_term_thesis_targets(sample_snapshot, portfolio_policy_config, sample_portfolio_analysis) -> list[dict]:
    return build_long_term_thesis_targets(
        sample_snapshot,
        portfolio_policy_config,
        sample_portfolio_analysis["resolved_buckets"],
        sample_portfolio_analysis["symbol_weights"],
    )


@pytest.fixture
def sample_computation(
    sample_snapshot,
    sample_portfolio_analysis,
    sample_market_references,
    sample_candidate_orders,
    sample_exposure_breakdown,
    sample_core_buy_materials,
    sample_long_term_thesis_targets,
    buy_rules_config,
) -> MonthlyComputation:
    core_buy_materials, core_warnings = sample_core_buy_materials
    warnings = list(sample_portfolio_analysis["warnings"])
    warnings.extend(build_validation_warnings(sample_snapshot.warnings))
    warnings.extend(build_exposure_validation_warnings(sample_exposure_breakdown))
    warnings.extend(core_warnings)
    return MonthlyComputation(
        snapshot=sample_snapshot,
        generated_at="2026-03-07T00:00:00Z",
        bucket_allocations=sample_portfolio_analysis["bucket_allocations"],
        market_references=sample_market_references,
        candidate_orders=sample_candidate_orders,
        warnings=warnings,
        semi_exposure_pct=sample_exposure_breakdown["semiconductor_exposure_total_pct"],
        liquidity_jpy=sample_portfolio_analysis["liquidity_jpy"],
        sox_buy_signal=calculate_sox_buy_signal(
            buy_rules_config,
            sample_market_references,
            bucket_allocations=sample_portfolio_analysis["bucket_allocations"],
            exposure_breakdown=sample_exposure_breakdown,
        ),
        portfolio_summary=sample_portfolio_analysis["portfolio_summary"],
        core_buy_materials=core_buy_materials,
        exposure_breakdown=sample_exposure_breakdown,
        long_term_thesis_targets=sample_long_term_thesis_targets,
        monthly_execution_outputs={
            "portfolio_management_mode": core_buy_materials.get("portfolio_management_mode"),
            "monthly_core_budget_tier": core_buy_materials.get("monthly_core_budget_tier"),
            "recommended_monthly_core_buy_budget_jpy": core_buy_materials.get(
                "recommended_monthly_core_buy_budget_jpy"
            ),
            "candidate_count": len(sample_candidate_orders),
        },
        quarterly_rule_review_outputs={
            "classification_override_count": 0,
            "classification_audit": sample_portfolio_analysis.get("classification_audit", []),
            "core_reference_missing_symbols": [],
            "direct_semiconductor_exposure_pct": sample_exposure_breakdown.get("direct_semiconductor_exposure_pct"),
            "indirect_ai_infra_exposure_pct": sample_exposure_breakdown.get("indirect_ai_infra_exposure_pct"),
        },
        metadata={
            "snapshot_path": str(ROOT / "data/normalized/snapshot_2026_03.yaml"),
            "resolved_buckets": sample_portfolio_analysis["resolved_buckets"],
            "classification_audit": sample_portfolio_analysis.get("classification_audit", []),
        },
    )


@pytest.fixture
def sample_review_text() -> str:
    return """【今月の指値提案】
- MSFT: 指値 468.00 USD, 1株, 理由: 20日平均からの押し目として妥当
- CIBR: 指値 94.00 USD, 1株, 理由: サイバーセキュリティ比率の補強
- URA: 指値 92.00 USD, 2株, 理由: ボラティリティを踏まえて少額継続

【コア定額買い方針レビュー】
- core は今月最低 10 万円は買う
- 今月は core を satellite より優先する

【SOX投信判定】
- 買う
- 理由: SMH が直近高値から -8% で買いゾーン内

【ポートフォリオ診断】
- 半導体エクスポージャはやや高い
- PLTR の比率が高い
- 今月は core を優先補強

【ルール改善レビュー】
- 半導体エクスポージャ警告をもう少し強めに出すべき
- PLTR の浅い押し目抑制は維持してよい

【Codex向け修正要約】
must:
- portfolio.py に半導体エクスポージャ警告の説明を追加
should:
- review_parser.py で理由抽出を安定化
nice_to_have:
- README に四半期見直し運用を追記
- 修正目的: 警告とレビューの整合性を上げる
- 変更すべき仕様: 半導体警告の説明を詳細化する
- 影響範囲: portfolio.py, README.md
- 推奨テスト: test_portfolio.py を更新
"""
