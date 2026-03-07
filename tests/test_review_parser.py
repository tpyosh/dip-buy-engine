from __future__ import annotations

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

