from __future__ import annotations

from decimal import Decimal

from monthly_limit_order_review.review_parser import parse_review_feedback


def test_review_parser_extracts_priorities_and_sections(sample_review_text: str) -> None:
    feedback = parse_review_feedback(sample_review_text)

    assert feedback.sox_decision == "買う"
    assert feedback.must == ["portfolio.py に半導体エクスポージャ警告の説明を追加"]
    assert feedback.should == ["review_parser.py で理由抽出を安定化"]
    assert feedback.nice_to_have[0] == "README に四半期見直し運用を追記"
    assert any(proposal.symbol == "MSFT" for proposal in feedback.order_proposals)


def test_review_parser_warns_when_sections_are_missing() -> None:
    feedback = parse_review_feedback("【今月の指値提案】\n- MSFT: 指値 468.00 USD, 1株\n")

    assert feedback.parser_warnings
    assert any("Section not found" in warning for warning in feedback.parser_warnings)


def test_review_parser_accepts_quarterly_rule_review_heading() -> None:
    feedback = parse_review_feedback(
        "【今月の指値提案】\n- MSFT: 指値 468.00 USD, 1株\n"
        "【SOX投信判定】\n- 買わない\n"
        "【ポートフォリオ診断】\n- core を優先\n"
        "【四半期ルール見直し】\n- 大きなルール変更提案なし\n"
        "【Codex向け修正要約】\n```md\nmust:\n- なし\n```"
    )

    assert "大きなルール変更提案なし" in feedback.rule_review


def test_review_parser_extracts_markdown_table_order_proposals() -> None:
    feedback = parse_review_feedback(
        "【今月の指値提案】\n"
        "| 銘柄 | 提案 | 理由 |\n"
        "| --- | ---: | --- |\n"
        "| CIBR | **今月は見送り** | ルール上の判断: satellite_core over target。 |\n"
        "| URA | 指値 45.38 USD（20営業日平均 53.3833 USD, 平均比 -14.99%）, 2株 | 深い押し目は許容。 |\n"
        "| PLTR | 指値 109.02 USD（20営業日平均 139.7678 USD, 平均比 -22.00%）, 2株 | 深い押し目だけ。 |\n"
        "| MSFT | 指値 377.30 USD（20営業日平均 419.2170 USD, 平均比 -10.00%）, 2株 | broad market core 優先。 |\n"
        "\nPython候補より減らしたもの\n"
        "* MSFT: 3段 → 1段。今月の裁量判断。\n"
        "【SOX投信判定】\n- 買わない\n"
        "【ポートフォリオ診断】\n- core を優先\n"
        "【四半期ルール見直し】\n- 大きなルール変更提案なし\n"
        "【Codex向け修正要約】\n```md\nmust:\n- なし\n```"
    )

    proposals = {proposal.symbol: proposal for proposal in feedback.order_proposals}
    assert proposals["CIBR"].recommended_price is None
    assert proposals["CIBR"].recommended_shares == 0
    assert proposals["URA"].recommended_price == Decimal("45.38")
    assert proposals["URA"].recommended_shares == 2
    assert proposals["PLTR"].recommended_price == Decimal("109.02")
    assert proposals["MSFT"].recommended_price == Decimal("377.30")
    assert proposals["MSFT"].recommended_shares == 2


def test_review_parser_stops_section_at_untracked_heading() -> None:
    feedback = parse_review_feedback(
        "【ポートフォリオ診断】\n"
        "- core を優先\n"
        "【長期シナリオレビュー】\n"
        "- これは portfolio_diagnosis ではない\n"
        "【SOX投信判定】\n"
        "- 買わない\n"
        "【今月の指値提案】\n"
        "- MSFT: 指値 468.00 USD, 1株\n"
        "【四半期ルール見直し】\n"
        "- 大きなルール変更提案なし\n"
        "【Codex向け修正要約】\n```md\nmust:\n- なし\n```"
    )

    assert feedback.portfolio_diagnosis == ["core を優先"]
