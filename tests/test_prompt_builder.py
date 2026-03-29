from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.prompt_builder import build_monthly_review_prompt


def test_monthly_review_prompt_contains_required_sections(sample_computation) -> None:
    template_path = Path(__file__).resolve().parents[1] / "prompts/templates/monthly_review_template.md"
    prompt = build_monthly_review_prompt(sample_computation, template_path.read_text(encoding="utf-8"))

    assert "## 1. 前提" in prompt
    assert "【要約】" in prompt
    assert "## 5. コア定額買い判定材料" in prompt
    assert "## 6. SOX 判定材料" in prompt
    assert "## 7. 半導体エクスポージャ内訳" in prompt
    assert "## 8. 長期シナリオ点検対象" in prompt
    assert "## 9. ChatGPTへの長期シナリオレビュー依頼" in prompt
    assert "## 11. 生成ロジック上の分離データ" in prompt
    assert "## 13. 必須の月次・四半期レビュー観点" in prompt
    assert "【Codex向け修正要約】" in prompt
    assert "【コア定額買い方針レビュー】" in prompt
    assert "【長期シナリオレビュー】" in prompt
    assert "【四半期ルール見直し】" in prompt
    assert "【ルール改善レビュー】" not in prompt
    assert "| ALL_COUNTRY_FUND |" in prompt
    assert "| MSFT | jun_core |" in prompt
    assert "suppressed_reason_code" in prompt
    assert "0段以上の任意段数" in prompt
    assert "ルール上の判断" in prompt
    assert "必ず単一の ```md コードブロックで出力すること" in prompt
    assert "無理に改善提案を作らない" in prompt
    assert "`must: なし`" in prompt
    assert "Webで確認した事実と、そこからの推論を分けて記述してください。" in prompt
    assert "monthly_core_budget_tier" in prompt
    assert "recommended_monthly_core_buy_budget_jpy" in prompt
    assert "rebalance_mode_active" in prompt
    assert "in_direct" in prompt
    assert "in_indirect" in prompt
    assert "priority_lowered_boolean" in prompt
    assert "月次の執行判断と、四半期単位のルール見直し提案は明確に分離してください。" in prompt
