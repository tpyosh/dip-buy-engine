from __future__ import annotations

from .prompt_renderer import render_chatgpt_prompt


def build_monthly_review_prompt(computation, template_text: str) -> str:
    return render_chatgpt_prompt(computation, template_text)
