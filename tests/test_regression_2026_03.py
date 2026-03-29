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
    mean_close_20d: str,
    recent_high_21d: str,
    recent_high_63d: str,
    currency: str,
) -> MarketReference:
    return MarketReference(
        symbol=symbol,
        yfinance_symbol=yfinance_symbol,
        current_price=Decimal(current_price),
        mean_close_20d=Decimal(mean_close_20d),
        recent_high_21d=Decimal(recent_high_21d),
        recent_high_63d=Decimal(recent_high_63d),
        currency=currency,
        as_of=date(2026, 3, 7),
    )


def fake_references(requests: dict[str, dict[str, str]]) -> list[MarketReference]:
    defaults = {
        "CIBR": dict(current_price="66.00", mean_close_20d="65.0615", recent_high_21d="70.50", recent_high_63d="76.00", currency="USD"),
        "URA": dict(current_price="48.78", mean_close_20d="53.1685", recent_high_21d="55.00", recent_high_63d="58.00", currency="USD"),
        "PLTR": dict(current_price="157.16", mean_close_20d="138.7620", recent_high_21d="175.00", recent_high_63d="200.00", currency="USD"),
        "MSFT": dict(current_price="408.96", mean_close_20d="401.1770", recent_high_21d="430.00", recent_high_63d="450.00", currency="USD"),
        "SMH": dict(current_price="380.56", mean_close_20d="390.00", recent_high_21d="403.00", recent_high_63d="426.16", currency="USD"),
        "USDJPY": dict(current_price="157.54", mean_close_20d="157.00", recent_high_21d="158.00", recent_high_63d="159.00", currency="JPY"),
        "RAKUTEN_ALL_COUNTRY_1": dict(current_price="110.00", mean_close_20d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", currency="USD"),
        "RAKUTEN_ALL_COUNTRY_2": dict(current_price="110.00", mean_close_20d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", currency="USD"),
        "EMAXIS_ALL_COUNTRY": dict(current_price="110.00", mean_close_20d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", currency="USD"),
        "EMAXIS_ALL_COUNTRY_TAXABLE": dict(current_price="110.00", mean_close_20d="108.00", recent_high_21d="112.00", recent_high_63d="115.00", currency="USD"),
        "RAKUTEN_SP500": dict(current_price="500.00", mean_close_20d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", currency="USD"),
        "EMAXIS_SP500_1": dict(current_price="500.00", mean_close_20d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", currency="USD"),
        "EMAXIS_SP500_2": dict(current_price="500.00", mean_close_20d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", currency="USD"),
        "EMAXIS_SP500_3": dict(current_price="500.00", mean_close_20d="490.00", recent_high_21d="510.00", recent_high_63d="520.00", currency="USD"),
    }

    references: list[MarketReference] = []
    for symbol, params in requests.items():
        reference_params = defaults[symbol]
        references.append(
            make_reference(
                symbol,
                params["yfinance_symbol"],
                current_price=reference_params["current_price"],
                mean_close_20d=reference_params["mean_close_20d"],
                recent_high_21d=reference_params["recent_high_21d"],
                recent_high_63d=reference_params["recent_high_63d"],
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

    assert "liquidity_above_range" in warning_codes
    assert "core_below_range" in warning_codes
    assert ura_candidate.suppressed_reason_code == "limit_above_current"
    assert {"SMH", "NISSEI_SOX_1", "NISSEI_SOX_2"} <= exposure_symbols
    assert msft_exposure["included_in_direct_semiconductor_exposure"] == "no"
    assert msft_exposure["included_in_indirect_ai_infra_exposure"] == "yes"
    assert {"URA", "PLTR", "CIBR", "MSFT"} <= thesis_symbols
    assert computation.core_buy_materials["core_constituents"]
    assert all_country_constituent["reference_symbol"] in {"VT", "ACWI"}
    assert computation.core_buy_materials["monthly_core_budget_tier"] == "rebalance"
    assert computation.core_buy_materials["recommended_monthly_core_buy_budget_jpy"] == 700000
    assert computation.monthly_execution_outputs["candidate_count"] == len(computation.candidate_orders)
    assert "classification_audit" in computation.quarterly_rule_review_outputs
    assert "candidate_count" not in computation.quarterly_rule_review_outputs
    assert "【要約】" in prompt
    assert "## 5. コア定額買い判定材料" in prompt
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
    assert "## 11. 生成ロジック上の分離データ" in prompt
    assert "## 13. 必須の月次・四半期レビュー観点" in prompt
    assert "priority_lowered_boolean: True" in prompt
    assert "四半期単位のルール見直し提案は明確に分離してください。" in prompt
