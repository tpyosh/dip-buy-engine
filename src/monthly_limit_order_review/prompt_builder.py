from __future__ import annotations

from .models import ReviewPacket
from .prompt_renderer import render_chatgpt_prompt


def build_monthly_review_prompt(
    computation,
    template_text: str,
    *,
    review_packet: ReviewPacket | None = None,
    financial_assumptions_text: str = "",
) -> str:
    return render_chatgpt_prompt(
        computation,
        template_text,
        review_packet=review_packet,
        financial_assumptions_text=financial_assumptions_text,
    )
