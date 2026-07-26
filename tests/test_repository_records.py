from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from monthly_limit_order_review.repository_records import (
    RepositoryIntegrityError,
    audit_repository,
    load_recurring_contribution_context,
)
from monthly_limit_order_review.storage import (
    default_output_paths,
    on_demand_output_paths,
)


ROOT = Path(__file__).resolve().parents[1]


def test_repository_audit_has_no_errors() -> None:
    issues = audit_repository(ROOT)

    assert [issue for issue in issues if issue["severity"] == "error"] == []


def test_recurring_contributions_load_from_versioned_plan_not_legacy_config() -> None:
    context = load_recurring_contribution_context(ROOT)

    assert context["legacy_fallback"] is False
    assert context["source_path"] == "plans/recurring/versions/2026-03-01.yaml"
    assert context["record"]["record_type"] == "observed_recurring_contribution_state"
    assert context["contributions"]["total_monthly_jpy"] == 750000


def test_recurring_pointer_cannot_escape_repository(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "core_recurring_contributions.yaml").write_text(
        'source_of_truth_ref: "../outside.yaml"\n',
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIntegrityError, match="within the repository"):
        load_recurring_contribution_context(tmp_path)


def test_generated_outputs_are_routed_under_reports() -> None:
    monthly = default_output_paths(ROOT, "2026_08")
    on_demand = on_demand_output_paths(
        ROOT,
        datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
    )

    assert monthly["computation"] == (
        ROOT / "reports/generated/monthly/2026_08/computation.yaml"
    )
    assert monthly["review_prompt"] == (
        ROOT / "reports/generated/monthly/2026_08/review_request.md"
    )
    assert on_demand["market_data"] == (
        ROOT
        / "reports/generated/on_demand/2026/2026_07_26T120000Z/market_data.yaml"
    )
    assert on_demand["prompt"] == (
        ROOT
        / "reports/generated/on_demand/2026/2026_07_26T120000Z/assessment_request.md"
    )
