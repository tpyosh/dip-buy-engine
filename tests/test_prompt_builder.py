from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.prompt_builder import build_monthly_review_prompt


def test_monthly_review_prompt_contains_required_sections(sample_computation) -> None:
    template_path = Path(__file__).resolve().parents[1] / "prompts/templates/monthly_review_template.md"
    prompt = build_monthly_review_prompt(sample_computation, template_path.read_text(encoding="utf-8"))

    assert "## 1. 前提" in prompt
    assert "## 5. SOX 判定材料" in prompt
    assert "【Codex向け修正要約】" in prompt
    assert "| MSFT |" in prompt
    assert "0段以上の任意段数" in prompt
    assert "ルール上の判断" in prompt
