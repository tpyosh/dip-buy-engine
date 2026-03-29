from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from monthly_limit_order_review.cli import compute_monthly
from monthly_limit_order_review.models import MarketReference
from monthly_limit_order_review.prompt_builder import build_monthly_review_prompt
from monthly_limit_order_review.storage import read_text

ROOT = Path(__file__).resolve().parents[1]


def make_reference(
    symbol: str,
    yfinance_symbol: str,
    *,
    current_price: str,
    mean_close_30d: str,
    recent_high_21d: str,
    recent_high_63d: str,
    prior_close_21d: str,
    prior_close_63d: str,
    currency: str,
) -> MarketReference:
    return MarketReference(
        symbol=symbol,
        yfinance_symbol=yfinance_symbol,
        current_price=Decimal(current_price),
        mean_close_20d=Decimal(mean_close_30d),
        recent_high_21d=Decimal(recent_high_21d),
        recent_high_63d=Decimal(recent_high_63d),
        currency=currency,
        as_of=date(2026, 3, 7),
        mean_close_30d=Decimal(mean_close_30d),
        prior_close_21d=Decimal(prior_close_21d),
        prior_close_63d=Decimal(prior_close_63d),
    )


def fake_references(requests: dict[str, dict[str, str]]) -> list[MarketReference]:
    defaults = {
        "CIBR": dict(current_price="66.00", mean_close_30d="65.0615", recent_high_21d="70.50", recent_high_63d="76.00", prior_close_21d="68.00", prior_close_63d="71.00", currency="USD"),
        "URA": dict(current_price="48.78", mean_close_30d="53.1685", recent_high_21d="55.00", recent_high_63d="58.00", prior_close_21d="50.00", prior_close_63d="54.00", currency="USD"),
        "PLTR": dict(current_price="157.16", mean_close_30d="138.7620", recent_high_21d="175.00", recent_high_63d="200.00", prior_close_21d="165.00", prior_close_63d="170.00", currency="USD"),
        "MSFT": dict(current_price="408.96", mean_close_30d="401.1770", recent_high_21d="430.00", recent_high_63d="450.00", prior_close_21d="420.00", prior_close_63d="430.00", currency="USD"),
        "SMH": dict(current_price="380.56", mean_close_30d="390.00", recent_high_21d="403.00", recent_high_63d="426.16", prior_close_21d="392.00", prior_close_63d="410.00", currency="USD"),
        "USDJPY": dict(current_price="157.54", mean_close_30d="157.00", recent_high_21d="158.00", recent_high_63d="159.00", prior_close_21d="156.00", prior_close_63d="155.00", currency="JPY"),
        "RAKUTEN_ALL_COUNTRY_1": dict(current_price="110.00", mean_close_30d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", prior_close_21d="113.00", prior_close_63d="118.00", currency="USD"),
        "RAKUTEN_ALL_COUNTRY_2": dict(current_price="110.00", mean_close_30d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", prior_close_21d="113.00", prior_close_63d="118.00", currency="USD"),
        "EMAXIS_ALL_COUNTRY": dict(current_price="110.00", mean_close_30d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", prior_close_21d="113.00", prior_close_63d="118.00", currency="USD"),
        "EMAXIS_ALL_COUNTRY_TAXABLE": dict(current_price="110.00", mean_close_30d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", prior_close_21d="113.00", prior_close_63d="118.00", currency="USD"),
        "RAKUTEN_SP500": dict(current_price="500.00", mean_close_30d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", prior_close_21d="515.00", prior_close_63d="530.00", currency="USD"),
        "EMAXIS_SP500_1": dict(current_price="500.00", mean_close_30d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", prior_close_21d="515.00", prior_close_63d="530.00", currency="USD"),
        "EMAXIS_SP500_2": dict(current_price="500.00", mean_close_30d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", prior_close_21d="515.00", prior_close_63d="530.00", currency="USD"),
        "EMAXIS_SP500_3": dict(current_price="500.00", mean_close_30d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", prior_close_21d="515.00", prior_close_63d="530.00", currency="USD"),
    }

    references: list[MarketReference] = []
    for symbol, params in requests.items():
        reference_params = defaults[symbol]
        references.append(
            make_reference(
                symbol,
                params["yfinance_symbol"],
                current_price=reference_params["current_price"],
                mean_close_30d=reference_params["mean_close_30d"],
                recent_high_21d=reference_params["recent_high_21d"],
                recent_high_63d=reference_params["recent_high_63d"],
                prior_close_21d=reference_params["prior_close_21d"],
                prior_close_63d=reference_params["prior_close_63d"],
                currency=reference_params["currency"],
            )
        )
    return references


def test_monthly_prompt_regression_2026_03(monkeypatch) -> None:
    monkeypatch.setattr("monthly_limit_order_review.cli.fetch_market_references", fake_references)

    snapshot_path = ROOT / "data/normalized/snapshot_2026_03.yaml"
    computation = compute_monthly(snapshot_path, project_root=ROOT)
    template_text = read_text(ROOT / "prompts/templates/monthly_review_template.md")
    prompt = build_monthly_review_prompt(computation, template_text)

    warning_codes = {warning.code for warning in computation.warnings}
    exposure_symbols = {item["symbol"] for item in computation.exposure_breakdown["breakdown"]}
    thesis_symbols = {item["symbol"] for item in computation.long_term_thesis_targets}
    ura_candidate = next(candidate for candidate in computation.candidate_orders if candidate.symbol == "URA")
    msft_exposure = next(item for item in computation.exposure_breakdown["breakdown"] if item["symbol"] == "MSFT")
    all_country_constituent = next(
        item for item in computation.core_buy_materials["core_constituents"] if item["symbol"] == "EMAXIS_ALL_COUNTRY"
    )
    toyota_audit = next(item for item in computation.metadata["classification_audit"] if item["symbol"] == "7203")

    assert "liquidity_above_range" in warning_codes
    assert "core_below_range" in warning_codes
    assert ura_candidate.suppressed_reason_code == "limit_above_current"
    assert {"SMH", "NISSEI_SOX_1", "NISSEI_SOX_2"} <= exposure_symbols
    assert msft_exposure["included_in_direct_semiconductor_exposure"] == "no"
    assert msft_exposure["included_in_indirect_ai_infra_exposure"] == "yes"
    assert {"URA", "PLTR", "CIBR", "MSFT"} <= thesis_symbols
    assert computation.core_buy_materials["core_constituents"]
    assert all_country_constituent["reference_symbol"] in {"VT", "ACWI"}
    assert toyota_audit["raw_bucket"] == "other"
    assert toyota_audit["resolved_bucket"] == "jun_core"
    assert toyota_audit["reason"] == "japan_large_cap_core_position_treated_as_jun_core"
    assert computation.core_buy_materials["monthly_core_budget_tier"] == "rebalance"
    assert computation.core_buy_materials["recommended_monthly_core_buy_budget_jpy"] == 700000
    assert computation.monthly_execution_outputs["candidate_count"] == len(computation.candidate_orders)
    assert computation.monthly_execution_outputs["core_recurring_contributions_total_jpy"] == 750000
    assert computation.monthly_execution_outputs["crypto_weekly_dca_total_jpy"] == 5000
    assert "classification_audit" in computation.quarterly_rule_review_outputs
    assert "candidate_count" not in computation.quarterly_rule_review_outputs
    assert "no_change" in computation.quarterly_rule_review_outputs
    assert "【要約】" in prompt
    assert "【今月のcoreスポット買い提案】" in prompt
    assert "## 5. コア定額買い判定材料" in prompt
    assert "## 5-1. Coreスポット買い判断材料" in prompt
    assert "## 7. 半導体エクスポージャ内訳" in prompt
    assert "## 8. 長期シナリオ点検対象" in prompt
    assert "## 9. ChatGPTへの長期シナリオレビュー依頼" in prompt
    assert "【コア定額買い方針レビュー】" in prompt
    assert "【長期シナリオレビュー】" in prompt
    assert "【四半期ルール見直し】" in prompt
    assert "【ルール改善レビュー】" not in prompt
    assert "必ず単一の ```md コードブロックで出力すること" in prompt
    assert "ハルシネーション防止" in prompt
    assert "`must: なし`" in prompt
    assert "Webで確認した事実と、そこからの推論を分けて記述してください。" in prompt
    assert "monthly_core_budget_tier: rebalance" in prompt
    assert "recommended_monthly_core_buy_budget_jpy: 700000" in prompt
    assert "0円は禁止" in prompt
    assert "単一具体額" in prompt
    assert "current_monthly_core_auto_invest_amount_jpy: 750000" in prompt
    assert "annualized_core_auto_invest_amount_jpy: 9000000" in prompt
    assert "current_cash_jpy:" in prompt
    assert "bond_like_holdings_present:" in prompt
    assert "## 11. 生成ロジック上の分離データ" in prompt
    assert "## 13. 必須の月次・四半期レビュー観点" in prompt
    assert "review_target_month: 2026_03" in prompt
    assert "指値設定基準値は直近30営業日の終値平均" in prompt
    assert "その指値が直近30営業日の終値平均から何%下かを必ず明示すること" in prompt
    assert "((指値 / 直近30営業日終値平均) - 1) * 100" in prompt
    assert "指値設定対象月キー: 2026_03" in prompt
    assert "## 5-2. Core積立設定（毎月固定）" in prompt
    assert "## 5-3. 暗号資産積立設定（毎週固定）" in prompt
    assert "total_monthly_jpy: 750000" in prompt
    assert "eMAXIS Slim 米国株式(S&P500)" in prompt
    assert "楽天・プラス・オールカントリー株式インデックス・ファンド" in prompt
    assert "| BTC | 2000 |" in prompt
    assert "| ETH | 2000 |" in prompt
    assert "| XRP | 1000 |" in prompt


def test_taxable_all_country_drawdown_is_not_null_after_reference_mapping(monkeypatch) -> None:
    monkeypatch.setattr("monthly_limit_order_review.cli.fetch_market_references", fake_references)

    snapshot_path = ROOT / "data/normalized/snapshot_2026_04.yaml"
    computation = compute_monthly(snapshot_path, project_root=ROOT)
    taxable = next(
        item for item in computation.core_buy_materials["core_constituents"] if item["symbol"] == "EMAXIS_ALL_COUNTRY_TAXABLE"
    )

    assert taxable["reference_symbol"] == "ACWI"
    assert taxable["drawdown_pct_from_recent_high"] is not None


def test_snapshot_2026_04_is_treated_as_april_limit_order_cycle(monkeypatch) -> None:
    monkeypatch.setattr("monthly_limit_order_review.cli.fetch_market_references", fake_references)

    snapshot_path = ROOT / "data/normalized/snapshot_2026_04.yaml"
    computation = compute_monthly(snapshot_path, project_root=ROOT)
    template_text = read_text(ROOT / "prompts/templates/monthly_review_template.md")
    prompt = build_monthly_review_prompt(computation, template_text)

    assert computation.metadata["review_target_month"] == "2026_04"
    assert computation.monthly_execution_outputs["review_target_month"] == "2026_04"
    assert "review_target_month: 2026_04" in prompt
    assert "指値設定対象月キー: 2026_04" in prompt
