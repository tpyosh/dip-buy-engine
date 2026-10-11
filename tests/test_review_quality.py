from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from monthly_limit_order_review.cli import main
from monthly_limit_order_review.independent_review import build_independent_review_input
from monthly_limit_order_review.review_quality import CHECKS, review_quality_issues

ROOT = Path(__file__).resolve().parents[1]
FAILED = ROOT / "tests/fixtures/independent_review/2026-10-11_failed_integration"


def synthetic_case() -> tuple[dict, dict, str]:
    """Fictional rubric examples, not recommendations for repository holdings."""
    source = "\n".join([
        "架空の評価ケース。一次資料と比較材料は確認済みとしてテストする。",
        "充足判定：相続特例は移行の時期を変えるが、分散へ移す方向は両条件で同じ。",
        "判断：相続銘柄は全10株を承認後に移行。特例ありなら適用期限前、なしなら通常の次回取引機会。",
        "集中銘柄は試験内の比較で税前倒しと集中削減の差を評価し、全20株を維持。費用差だけでは選ばない。",
        "コアは全30口を維持。変更案の機会利益より現状の分散・非課税価値が勝るとの試験内判断。",
        "同一拠出、生活維持、全世界株式案との比較、20%嗜好を尊重。最適比率と断定せず。",
        "統合は判断と条件を保持。未知は取得費加算額だけ。本人が税務書類を承認前に確認し結果別の時期を選ぶ。",
        "提案のみで正本・注文・取引は変更しない。次回は条件確認後、条件変化時は早期見直し。",
    ])
    symbols = ("CASE_INHERITED", "CASE_CONCENTRATED", "CASE_CORE")
    review_input = {"portfolio_snapshot": {"holdings": [
        {"symbol": symbols[0], "account_type": "特定口座", "quantity": 10},
        {"symbol": symbols[1], "account_type": "特定口座", "quantity": 20},
        {"symbol": symbols[2], "account_type": "NISA成長投資枠", "quantity": 30},
        {"symbol": "NON_TRADABLE", "account_type": None},
    ]}}
    checks = {name: {"verdict": "pass", "reason": "試験本文に該当する比較・判断・制約を示した。",
                     "evidence_lines": list(range(1, 9))} for name in CHECKS}
    rows = []
    for symbol, quantity in zip(symbols, (10, 20, 30)):
        rows.append({"symbol": symbol, "decision_class": "hold", "action": "確認済み全量を維持",
                     "rationale": "試験本文の税・分散・非課税価値の比較による積極的な保有判断",
                     "comparison": "変更案の利益と税・費用・集中リスクを比較して選択した",
                     "timing": "現在から条件変化まで。次回は条件確認後に見直す",
                     "next_step": "維持について発注操作なし。条件変化時に見直す",
                     "quantity": quantity, "method": "対象外（維持のため注文不要）",
                     "evidence_lines": [4, 5, 8], "unknowns": []})
    rows[0].update({"decision_class": "conditional", "action": "全量移行を提案",
                    "rationale": "両税務条件で分散移行を選ぶが時期を分ける",
                    "timing": "特例ありなら期限前、なしなら通常の次回取引機会",
                    "next_step": "本人が承認前に税務書類を確認し、条件別の時期を承認する",
                    "method": "成行の提案。本人承認後に発注", "evidence_lines": [2, 3, 7]})
    rows[0]["unknowns"] = [{"field": "tax_credit", "reason": "相続特例の適用未確認",
        "impact": "decision", "materiality": "移行方向は共通だが実行時期を変える",
        "owner": "本人", "verification": "税務書類と適用期限を照合",
        "verify_by": "提案承認前。期限が近ければ優先確認",
        "branches": ["適用あり：期限前の移行を提案", "適用なし：通常の次回取引機会の移行を提案"]}]
    return {"schema_version": 1, "source_ref": "response.md", "source_sha256": sha256(source.encode()).hexdigest(),
            "checks": checks, "holdings": rows,
            "majority_review": {"symbols": [], "check": {"verdict": "pass", "reason": "多数保留なし",
                                                            "evidence_lines": [3, 4, 5]}}}, review_input, source


def test_a_research_decision_integration_example_has_a_reasoned_action() -> None:
    assessment, review_input, source = synthetic_case()
    assert review_quality_issues(assessment, review_input, source) == []
    assessment["checks"]["decision_stage"]["verdict"] = "unknown"
    assert "check:decision_stage" in review_quality_issues(assessment, review_input, source)


def test_b_inheritance_tax_unknown_does_not_block_unrelated_decisions() -> None:
    assessment, review_input, source = synthetic_case()
    assert assessment["holdings"][0]["decision_class"] == "conditional"
    assert assessment["holdings"][1]["decision_class"] == "hold"
    assert review_quality_issues(assessment, review_input, source) == []
    assessment["holdings"][0]["unknowns"][0]["branches"] = []
    assert "CASE_INHERITED:tax_credit:missing_branches" in review_quality_issues(assessment, review_input, source)
    assessment["holdings"][0]["unknowns"][0]["impact"] = "implementation"
    assert "CASE_INHERITED:no_decision_changing_unknown" in review_quality_issues(assessment, review_input, source)


def test_c_large_gain_requires_comparison_but_does_not_force_sale() -> None:
    assessment, review_input, source = synthetic_case()
    assert review_quality_issues(assessment, review_input, source) == []
    assessment["holdings"][1]["comparison"] = None
    assessment["checks"]["tax_and_concentration"]["verdict"] = "fail"
    issues = review_quality_issues(assessment, review_input, source)
    assert "CASE_CONCENTRATED:missing_comparison" in issues
    assert "check:tax_and_concentration" in issues


def test_d_unknown_quantity_requires_impact_verification_and_branches() -> None:
    assessment, review_input, source = synthetic_case()
    row = assessment["holdings"][0]
    row["quantity"] = None
    assert "CASE_INHERITED:unjustified_null_quantity" in review_quality_issues(assessment, review_input, source)
    unknown = deepcopy(row["unknowns"][0])
    unknown.update(field="quantity", impact="implementation", reason="試験用：正確な数量は未確認",
                   materiality="移行方針は決められるが正確な発注数量には影響する",
                   branches=["数量確認後：確認済み持分全量の案を再計算", "矛盾あり：該当数量だけ再確認"])
    row["unknowns"].append(unknown)
    assert review_quality_issues(assessment, review_input, source) == []
    assessment["checks"]["grounded_values"]["verdict"] = "fail"
    assert "check:grounded_values" in review_quality_issues(assessment, review_input, source)


@pytest.mark.parametrize("check", ["preference_respected", "preference_not_claimed_optimal"])
def test_e_respects_twenty_percent_without_claiming_optimality(check: str) -> None:
    assessment, review_input, source = synthetic_case()
    assessment["checks"][check]["verdict"] = "fail"
    assert f"check:{check}" in review_quality_issues(assessment, review_input, source)


def test_f_rejects_actual_failed_integration_and_generic_next_steps() -> None:
    assessment = yaml.safe_load((FAILED / "assessment.yaml").read_text())
    review_input = build_independent_review_input(ROOT, ROOT / "data/normalized/snapshot_2026_10.yaml")
    source = (FAILED / "response.md").read_text()
    issues = review_quality_issues(assessment, review_input, source)
    assert "check:status_quo_comparison" in issues
    assert "check:next_step_actionability" in issues
    assert "majority_deferral_not_rechecked" in issues
    assert "7203:quantity:missing_branches" in issues
    assert "NISSEI_SOX_1:missing_comparison" in issues
    assert "holding_coverage_mismatch" not in issues
    assert "source_hash_mismatch" not in issues
    # The historical failure would still fail even with every holding row present.
    assert len(assessment["holdings"]) == 14


def test_g_annotation_checker_is_read_only_and_rejects_unsafe_promotion(tmp_path: Path) -> None:
    assessment, review_input, source = synthetic_case()
    assessment["checks"]["proposal_safety"]["verdict"] = "fail"
    assert "check:proposal_safety" in review_quality_issues(assessment, review_input, source)
    (tmp_path / "response.md").write_text(source)
    (tmp_path / "assessment.yaml").write_text(yaml.safe_dump(assessment))
    (tmp_path / "input.yaml").write_text(yaml.safe_dump(review_input))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert main(["check-review-quality", "--assessment", str(tmp_path / "assessment.yaml"),
                 "--review-input", str(tmp_path / "input.yaml")]) == 2
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


def test_many_justified_holds_pass_without_manufacturing_trades() -> None:
    assessment, review_input, source = synthetic_case()
    row = assessment["holdings"][0]
    row.update(decision_class="hold", action="確認済み全量維持", method="対象外", unknowns=[],
               rationale="試験内で税・分散と変更案を比較し維持を選択", timing="現在から条件変化まで",
               next_step="維持に発注操作なし。条件変化時に再判断")
    source = source.replace("充足判定：相続特例は移行の時期を変えるが、分散へ移す方向は両条件で同じ。",
                            "充足判定：試験内では3明細とも比較に必要な証拠は十分で、未知による判断保留はない。")
    source = source.replace("判断：相続銘柄は全10株を承認後に移行。特例ありなら適用期限前、なしなら通常の次回取引機会。",
                            "判断：相続銘柄も変更案と比較し、試験内では全10株維持を選択。")
    source = source.replace("統合は判断と条件を保持。未知は取得費加算額だけ。本人が税務書類を承認前に確認し結果別の時期を選ぶ。",
                            "統合は判断と条件を保持。全量維持には発注操作不要で、条件変化時に再判断する。")
    assessment["source_sha256"] = sha256(source.encode()).hexdigest()
    assert review_quality_issues(assessment, review_input, source) == []


def test_many_conditionals_require_individual_recheck_not_an_aggregate_claim() -> None:
    assessment, review_input, source = synthetic_case()
    assessment["holdings"][1] = {**deepcopy(assessment["holdings"][0]), "symbol": "CASE_CONCENTRATED"}
    assert "majority_deferral_not_rechecked" in review_quality_issues(assessment, review_input, source)
    assessment["majority_review"]["symbols"] = ["CASE_INHERITED", "CASE_CONCENTRATED"]
    assert review_quality_issues(assessment, review_input, source) == []


@pytest.mark.parametrize("mutation, issue", [
    ("hash", "source_hash_mismatch"), ("line", "evidence_line_out_of_range"),
    ("duplicate", "duplicate_holding_id"), ("omit", "holding_coverage_mismatch"),
])
def test_evidence_and_coverage_integrity(mutation: str, issue: str) -> None:
    assessment, review_input, source = synthetic_case()
    if mutation == "hash":
        source += "changed"
    elif mutation == "line":
        assessment["holdings"][0]["evidence_lines"] = [9999]
    elif mutation == "duplicate":
        assessment["holdings"].append(deepcopy(assessment["holdings"][0]))
    else:
        assessment["holdings"].pop()
    assert issue in review_quality_issues(assessment, review_input, source)
