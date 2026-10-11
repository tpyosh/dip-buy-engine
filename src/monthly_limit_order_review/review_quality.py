"""Check Codex's evidence-backed annotations; do not infer investment merit from prose."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import jsonschema

from .storage import load_yaml

ROOT = Path(__file__).resolve().parents[2]
CHECKS = (
    "evidence_sufficiency", "decision_stage", "status_quo_comparison",
    "all_country_comparison", "tax_and_concentration", "lifestyle_common_contributions",
    "preference_respected", "preference_not_claimed_optimal", "proposal_safety",
    "integration_preserves_decisions", "next_review",
    "grounded_values", "next_step_actionability",
)


def review_quality_issues(assessment: dict, review_input: dict, source_text: str) -> list[str]:
    """Return contract gaps, including annotations marked fail or unknown.

    A human/Codex must first compare each annotation with the cited answer lines.
    Passing this check does not prove financial optimality or model performance.
    """
    schema = load_yaml(ROOT / "schemas/independent-review-quality.schema.yaml")
    jsonschema.Draft202012Validator(schema).validate(assessment)
    issues: list[str] = []
    if assessment["source_sha256"] != sha256(source_text.encode()).hexdigest():
        issues.append("source_hash_mismatch")
    line_count = len(source_text.splitlines())
    for name in CHECKS:
        check = assessment["checks"].get(name)
        if not check or check["verdict"] != "pass":
            issues.append(f"check:{name}")
    if set(assessment["checks"]) - set(CHECKS):
        issues.append("unknown_check_id")
    expected = {h["symbol"] for h in review_input["portfolio_snapshot"]["holdings"]
                if (h.get("account_type") or "").startswith(("NISA", "特定口座", "一般口座"))}
    rows = assessment["holdings"]
    symbols = [row["symbol"] for row in rows]
    if len(set(symbols)) != len(symbols):
        issues.append("duplicate_holding_id")
    if set(symbols) != expected:
        issues.append("holding_coverage_mismatch")
    recheck: set[str] = set()
    for row in rows:
        symbol = row["symbol"]
        for field in ("action", "rationale", "comparison", "timing", "next_step"):
            if not row[field] or not row[field].strip():
                issues.append(f"{symbol}:missing_{field}")
        unknowns = {u["field"]: u for u in row["unknowns"]}
        if len(unknowns) != len(row["unknowns"]):
            issues.append(f"{symbol}:duplicate_unknown_field")
        for field in ("quantity", "method"):
            if row[field] is None and field not in unknowns:
                issues.append(f"{symbol}:unjustified_null_{field}")
        for u in row["unknowns"]:
            for field in ("reason", "materiality", "owner", "verification", "verify_by"):
                if not u[field] or not u[field].strip():
                    issues.append(f"{symbol}:{u['field']}:missing_{field}")
            if not u["branches"]:
                issues.append(f"{symbol}:{u['field']}:missing_branches")
        if row["decision_class"] in ("conditional", "deferred"):
            if not any(u["impact"] == "decision" for u in row["unknowns"]):
                issues.append(f"{symbol}:no_decision_changing_unknown")
        if (row["decision_class"] in ("conditional", "deferred")
                or row["quantity"] is None or row["method"] is None):
            recheck.add(symbol)
    majority = assessment["majority_review"]
    if rows and len(recheck) * 2 > len(rows):
        if set(majority["symbols"]) != recheck or majority["check"]["verdict"] != "pass":
            issues.append("majority_deferral_not_rechecked")
    if set(majority["symbols"]) - set(symbols):
        issues.append("majority_unknown_holding_id")
    evidence_groups = [c["evidence_lines"] for c in assessment["checks"].values()]
    evidence_groups += [row["evidence_lines"] for row in rows]
    evidence_groups.append(majority["check"]["evidence_lines"])
    if any(line > line_count for group in evidence_groups for line in group):
        issues.append("evidence_line_out_of_range")
    return issues
