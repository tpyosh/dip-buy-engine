from __future__ import annotations

from decimal import Decimal

from .models import CandidateOrder, PortfolioWarning, ProposalDiff, ReviewFeedback
from .utils import quantize


def build_proposal_diffs(
    candidate_orders: list[CandidateOrder],
    review_feedback: ReviewFeedback,
    python_warnings: list[PortfolioWarning],
) -> list[ProposalDiff]:
    python_map = select_primary_candidates(candidate_orders)
    review_map = {proposal.symbol: proposal for proposal in review_feedback.order_proposals}
    normalized_python_warnings = [warning.message.lower() for warning in python_warnings]
    added_warnings = [
        warning
        for warning in review_feedback.portfolio_diagnosis
        if not any(warning.lower() in base or base in warning.lower() for base in normalized_python_warnings)
    ]

    diffs: list[ProposalDiff] = []
    for symbol in sorted(set(python_map) | set(review_map)):
        python_candidate = python_map.get(symbol)
        review_candidate = review_map.get(symbol)
        price_diff_pct = None
        if (
            python_candidate is not None
            and python_candidate.limit_price not in (None, Decimal("0"))
            and review_candidate is not None
            and review_candidate.recommended_price is not None
        ):
            if python_candidate.limit_price != 0:
                price_diff_pct = quantize(
                    (
                        (review_candidate.recommended_price - python_candidate.limit_price)
                        / python_candidate.limit_price
                    )
                    * Decimal("100"),
                    2,
                )

        diffs.append(
            ProposalDiff(
                symbol=symbol,
                python_price=python_candidate.limit_price if python_candidate is not None else None,
                chatgpt_price=review_candidate.recommended_price if review_candidate is not None else None,
                price_diff_pct=price_diff_pct,
                python_shares=python_candidate.shares if python_candidate is not None else None,
                chatgpt_shares=review_candidate.recommended_shares if review_candidate is not None else None,
                reason_summary=(
                    review_candidate.reason
                    if review_candidate is not None
                    else "ChatGPT review did not include a proposal for this symbol."
                ),
                added_warnings=added_warnings,
                candidate_removed=python_candidate is not None and review_candidate is None,
            )
        )
    return diffs


def select_primary_candidates(candidate_orders: list[CandidateOrder]) -> dict[str, CandidateOrder]:
    selected: dict[str, CandidateOrder] = {}
    for candidate in candidate_orders:
        current = selected.get(candidate.symbol)
        if current is None:
            selected[candidate.symbol] = candidate
            continue
        if current.suppressed and not candidate.suppressed:
            selected[candidate.symbol] = candidate
    return selected
