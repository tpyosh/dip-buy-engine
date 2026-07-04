from __future__ import annotations

from decimal import Decimal
from datetime import date

from monthly_limit_order_review.calendar_events import build_core_spot_buy_calendar_event_drafts
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


def test_review_parser_extracts_block_order_proposals() -> None:
    feedback = parse_review_feedback(
        "【今月の指値提案】\n"
        "対象月: **2026_07**\n\n"
        "CIBR: **今月は見送り**\n"
        "ルール上の判断: satellite_core が over target。\n\n"
        "URA: **1段**\n"
        "指値 **40.65 USD**（20営業日平均 **47.8267 USD**, 平均比 **-15.01%**）\n"
        "株数: **2株**\n\n"
        "ルール上の判断: 浅い段は見送り。\n\n"
        "PLTR: **1段**\n"
        "指値 **104.15 USD**（20営業日平均 **133.5195 USD**, 平均比 **-22.00%**）\n"
        "株数: **2株**\n\n"
        "MSFT: **1段**\n"
        "指値 **365.67 USD**（20営業日平均 **406.2960 USD**, 平均比 **-10.00%**）\n"
        "株数: **1株**\n"
        "-18%の深い段は今月は見送りします。\n"
        "SOX投信 / SMH: **指値・追加買いなし**\n"
    )

    proposals = {proposal.symbol: proposal for proposal in feedback.order_proposals}
    assert proposals["CIBR"].recommended_price is None
    assert proposals["CIBR"].recommended_shares == 0
    assert proposals["URA"].recommended_price == Decimal("40.65")
    assert proposals["URA"].recommended_shares == 2
    assert proposals["PLTR"].recommended_price == Decimal("104.15")
    assert proposals["PLTR"].recommended_shares == 2
    assert proposals["MSFT"].recommended_price == Decimal("365.67")
    assert proposals["MSFT"].recommended_shares == 1


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


def test_review_parser_extracts_core_spot_buy_schedule() -> None:
    feedback = parse_review_feedback(
        "以下、2026_06 月次レビュー用データを前提にした判断です。\n"
        "【今月のcoreスポット買い提案】\n"
        "**900,000円**\n"
        "account_type: **特定口座**\n"
        "固定core積立額: **100,000円/月**\n"
        "coreスポット買い提案額: **900,000円**\n"
        "固定積立 + スポット買い合計: **1,000,000円**\n"
        "rule-based band: **aggressive**\n"
        "配分先内訳\n"
        "* eMAXIS Slim 全世界株式(オール・カントリー)(オルカン): **585,000円**\n"
        "* eMAXIS Slim 米国株式(S&P500): **315,000円**\n"
        "* 合計: **900,000円**\n"
        "実行方法: **4分割**\n"
        "実行スケジュール\n"
        "* 6月1日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 200,000円\n"
        "* 6月1日: eMAXIS Slim 米国株式(S&P500) 100,000円\n"
        "* 6月8日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 150,000円\n"
        "* 6月8日: eMAXIS Slim 米国株式(S&P500) 75,000円\n"
        "* 6月15日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 125,000円\n"
        "* 6月15日: eMAXIS Slim 米国株式(S&P500) 70,000円\n"
        "* 6月22日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 110,000円\n"
        "* 6月22日: eMAXIS Slim 米国株式(S&P500) 70,000円\n"
        "判断根拠\n"
        "* core不足\n",
        review_target_month="2026_06",
    )

    plan = feedback.core_spot_buy_plan
    assert plan is not None
    assert plan.total_amount_jpy == 900000
    assert plan.account_type == "特定口座"
    assert plan.fixed_core_auto_invest_amount_jpy == 100000
    assert plan.spot_buy_amount_jpy == 900000
    assert plan.total_core_deployment_jpy == 1000000
    assert plan.rule_based_band == "aggressive"
    assert plan.execution_method == "4分割"
    assert len(plan.allocations) == 2
    assert sum(item.amount_jpy for item in plan.allocations) == 900000
    assert len(plan.schedule) == 8
    assert plan.schedule[0].execution_date == date(2026, 6, 1)
    assert sum(item.amount_jpy for item in plan.schedule) == 900000
    assert not plan.parser_warnings


def test_calendar_event_drafts_group_core_spot_buy_schedule_by_date() -> None:
    feedback = parse_review_feedback(
        "【今月のcoreスポット買い提案】\n"
        "300,000円\n"
        "account_type: 特定口座\n"
        "実行スケジュール\n"
        "- 2026-06-01: eMAXIS Slim 全世界株式(オール・カントリー) 200,000円\n"
        "- 2026-06-01: eMAXIS Slim 米国株式(S&P500) 100,000円\n",
        review_target_month="2026_06",
    )

    drafts = build_core_spot_buy_calendar_event_drafts(
        feedback,
        review_target_month="2026_06",
        source_review_path="data/history/reviews/chatgpt_review_2026_06.txt",
        config={"default_start_time": "09:30", "duration_minutes": 20},
    )

    assert len(drafts) == 1
    request = drafts[0]["google_calendar_request"]
    assert drafts[0]["event_key"] == "core_spot_buy:2026_06:2026-06-01"
    assert drafts[0]["day_total_jpy"] == 300000
    assert request["title"] == "Coreスポット買い 300,000円"
    assert request["start_time"] == "2026-06-01T09:30:00+09:00"
    assert request["end_time"] == "2026-06-01T09:50:00+09:00"
    assert request["add_google_meet"] is False
    assert request["transparency"] == "transparent"
    assert "自動発注ではありません" in request["description"]
