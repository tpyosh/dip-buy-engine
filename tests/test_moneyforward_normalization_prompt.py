from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_moneyforward_prompt_requires_lossless_capture_coverage() -> None:
    prompt = (ROOT / "prompts/moneyforward_normalization_prompt.md").read_text(
        encoding="utf-8"
    )

    required_contract_terms = (
        "無欠落抽出契約",
        "この文面とキャプチャを受け取ったChatGPT自身に直接適用",
        "表示情報の重要度を判断して省略、統合、丸め、代表値化する権限はありません",
        "source_evidence.capture_inventory",
        "source_evidence.coverage_check.status",
        "blocked_unmapped_rows",
        "unmapped_source_rows",
        "account_type_source",
        "最新のカテゴリ合計だけを転記して、古い明細を残すような時点混在をしない",
        "source_evidence.privacy_redactions",
    )
    for term in required_contract_terms:
        assert term in prompt


def test_moneyforward_prompt_requires_group_heading_account_types_per_holding() -> None:
    prompt = (ROOT / "prompts/moneyforward_normalization_prompt.md").read_text(
        encoding="utf-8"
    )

    assert "配下の各明細へ個別に転記" in prompt
    assert "groupingとして扱い、配下の各明細へ同じ`account_type`を転記" in prompt
    assert "次の見出し以降へは引き継がない" in prompt
