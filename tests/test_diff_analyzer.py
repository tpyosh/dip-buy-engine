from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.diff_analyzer import build_proposal_diffs
from monthly_limit_order_review.review_parser import parse_review_feedback
from monthly_limit_order_review.storage import write_yaml


def test_proposal_diffs_capture_removed_candidates(
    tmp_path: Path,
    sample_candidate_orders,
    sample_portfolio_analysis,
    sample_review_text: str,
) -> None:
    feedback = parse_review_feedback(sample_review_text)
    diffs = build_proposal_diffs(sample_candidate_orders, feedback, sample_portfolio_analysis["warnings"])

    pltr_diff = next(diff for diff in diffs if diff.symbol == "PLTR")
    msft_diff = next(diff for diff in diffs if diff.symbol == "MSFT")

    assert pltr_diff.candidate_removed is True
    assert msft_diff.price_diff_pct is not None

    path = write_yaml(tmp_path / "diff.yaml", diffs)
    assert path.exists()
    assert "MSFT" in path.read_text(encoding="utf-8")

