from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.codex_patch_builder import (
    build_codex_patch_prompt,
    build_codex_patch_request,
)
from monthly_limit_order_review.diff_analyzer import build_proposal_diffs
from monthly_limit_order_review.models import ReviewFeedback
from monthly_limit_order_review.review_parser import parse_review_feedback


def test_codex_patch_prompt_contains_required_elements(
    sample_candidate_orders,
    sample_portfolio_analysis,
    sample_review_text: str,
) -> None:
    feedback = parse_review_feedback(sample_review_text)
    diffs = build_proposal_diffs(sample_candidate_orders, feedback, sample_portfolio_analysis["warnings"])
    request = build_codex_patch_request("2026_03", feedback, diffs)
    template_path = Path(__file__).resolve().parents[1] / "prompts/templates/codex_patch_template.md"
    prompt = build_codex_patch_prompt(template_path.read_text(encoding="utf-8"), request, diffs)

    assert "現在の問題:" in prompt
    assert "修正対象ファイル:" in prompt
    assert "追加 / 更新テスト:" in prompt
    assert "src/monthly_limit_order_review/portfolio.py" in prompt


def test_codex_patch_request_normalizes_readme_monthly_review_history_rule() -> None:
    feedback = ReviewFeedback(
        raw_text="",
        sections={},
        order_proposals=[],
        sox_decision=None,
        portfolio_diagnosis=[],
        rule_review=[],
        must=["なし"],
        should=[
            "README.md の当月セクション内の見やすい位置に「今月の指値買い設定」を追加または更新する",
        ],
        nice_to_have=[
            "コード修正提案が少ない月でも README.md に当月の運用要約と指値買い設定を確実に反映する",
        ],
    )

    request = build_codex_patch_request("2026_06", feedback, [])

    assert "README.md" in request.target_files
    assert any("最新月セクション" in item for item in request.should)
    assert all("当月セクション" not in item for item in [*request.should, *request.nice_to_have])
    assert any("月次レビュー履歴を蓄積せず" in item for item in request.should)
    assert any("過去月の `Monthly Review` セクションを残さない" in item for item in request.should)
