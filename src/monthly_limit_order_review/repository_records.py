from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .snapshot_loader import load_snapshot
from .storage import default_output_paths, load_yaml, on_demand_output_paths
from .strategy_policy import load_current_strategy_context


class RepositoryIntegrityError(ValueError):
    """Raised when repository records or references are inconsistent."""


def load_recurring_contribution_context(project_root: Path) -> dict:
    root = project_root.resolve()
    compatibility_path = root / "config/core_recurring_contributions.yaml"
    compatibility = load_yaml(compatibility_path)

    pointer_ref = compatibility.get("source_of_truth_ref")
    if pointer_ref is None:
        return {
            "compatibility": compatibility,
            "pointer": {},
            "record": compatibility,
            "contributions": deepcopy(
                compatibility.get("core_recurring_contributions", {})
            ),
            "source_path": str(compatibility_path),
            "legacy_fallback": True,
        }

    pointer_path = resolve_repository_path(
        root,
        pointer_ref,
        field="config/core_recurring_contributions.yaml source_of_truth_ref",
    )
    pointer = load_yaml(pointer_path)
    record_ref = pointer.get("active_record_path")
    if not record_ref:
        raise RepositoryIntegrityError(
            "plans/recurring/current.yaml must define active_record_path"
        )

    record_path = resolve_repository_path(
        root,
        record_ref,
        field="plans/recurring/current.yaml active_record_path",
    )
    record = load_yaml(record_path)
    contributions = record.get("core_recurring_contributions")
    if not isinstance(contributions, dict) or not contributions:
        raise RepositoryIntegrityError(
            f"Recurring contribution record must contain core_recurring_contributions: {record_path}"
        )

    return {
        "compatibility": compatibility,
        "pointer": pointer,
        "record": record,
        "contributions": deepcopy(contributions),
        "source_path": str(record_path.relative_to(root)),
        "legacy_fallback": False,
    }


def load_thesis_monitoring_policy(project_root: Path) -> dict[str, dict]:
    root = project_root.resolve()
    index = load_yaml(root / "strategy/theses/index.yaml")
    priorities = {"URA": "high", "PLTR": "medium", "CIBR": "medium", "MSFT": "medium"}
    policy: dict[str, dict] = {}
    for entry in index.get("entries", []):
        thesis_path = resolve_repository_path(
            root,
            entry.get("thesis_ref"),
            field="strategy/theses/index.yaml thesis_ref",
        )
        thesis = load_yaml(thesis_path)
        symbol = thesis.get("symbol")
        if symbol in (None, ""):
            continue
        policy[str(symbol)] = {
            "enabled": True,
            "thesis_id": thesis.get("thesis_id"),
            "thesis_status": entry.get("status") or thesis.get("status"),
            "long_term_thesis_summary": thesis.get("legacy_summary"),
            "key_risk_if_thesis_breaks": thesis.get("legacy_break_conditions", []),
            "review_priority": priorities.get(str(symbol), "medium"),
        }
    return policy


def resolve_repository_path(root: Path, ref: str, *, field: str) -> Path:
    path = (root / str(ref)).resolve()
    if not path.is_relative_to(root):
        raise RepositoryIntegrityError(f"{field} must stay within the repository")
    if not path.exists():
        raise RepositoryIntegrityError(f"{field} does not exist: {ref}")
    return path


def audit_repository(project_root: Path) -> list[dict[str, str]]:
    root = project_root.resolve()
    issues: list[dict[str, str]] = []

    required_paths = [
        "FINANCIAL_ASSUMPTIONS.md",
        "strategy/current.yaml",
        "plans/README.md",
        "plans/recurring/current.yaml",
        "transactions/ledger.yaml",
        "retrospectives/index.yaml",
        "reports/legacy-index.yaml",
        "data/raw/index.yaml",
        "schemas/snapshot.schema.yaml",
        "schemas/strategy.schema.yaml",
        "schemas/plan.schema.yaml",
        "schemas/transaction.schema.yaml",
        "schemas/retrospective.schema.yaml",
    ]
    for relative_path in required_paths:
        if not (root / relative_path).exists():
            _add_issue(
                issues,
                "error",
                "required_path_missing",
                f"Required repository path is missing: {relative_path}",
            )

    strategy_context: dict = {}
    try:
        strategy_context = load_current_strategy_context(root)
    except Exception as exc:  # noqa: BLE001
        _add_issue(issues, "error", "strategy_context_invalid", str(exc))

    if strategy_context:
        strategy = strategy_context["strategy"]
        financial_ref = strategy.get("scope", {}).get("financial_context_ref")
        _audit_reference(
            root,
            financial_ref,
            issues,
            code="financial_context_ref_invalid",
            required=True,
        )
        semiconductor_ref = (
            strategy.get("risk_limits", {})
            .get("direct_themes", {})
            .get("semiconductor", {})
            .get("thesis_ref")
        )
        _audit_reference(
            root,
            semiconductor_ref,
            issues,
            code="strategy_thesis_ref_invalid",
            required=True,
        )

        pointer = strategy_context["pointer"]
        active_plan_refs = pointer.get("active_plan_paths", [])
        active_plans = strategy_context["active_plans"]
        if len(active_plan_refs) != len(active_plans):
            _add_issue(
                issues,
                "error",
                "active_plan_count_mismatch",
                "Active plan references and loaded plans do not match.",
            )
        for plan_ref, plan in zip(active_plan_refs, active_plans, strict=False):
            _audit_plan(root, plan_ref, plan, strategy, issues)

    recurring_context: dict = {}
    try:
        recurring_context = load_recurring_contribution_context(root)
    except Exception as exc:  # noqa: BLE001
        _add_issue(issues, "error", "recurring_context_invalid", str(exc))
    if recurring_context and recurring_context.get("legacy_fallback"):
        _add_issue(
            issues,
            "warning",
            "recurring_context_legacy_fallback",
            "Recurring contributions still use the legacy config payload.",
        )

    _audit_snapshots(root, issues)
    _audit_raw_index(root, issues)
    _audit_transaction_ledger(root, issues)
    _audit_retrospective_index(root, issues)
    _audit_thesis_index(root, issues)
    _audit_legacy_markers(root, issues)
    _audit_output_routing(root, issues)
    return issues


def raise_for_repository_errors(issues: list[dict[str, str]]) -> None:
    errors = [issue for issue in issues if issue["severity"] == "error"]
    if errors:
        summary = "; ".join(
            f"{issue['code']}: {issue['message']}" for issue in errors
        )
        raise RepositoryIntegrityError(summary)


def _audit_plan(
    root: Path,
    plan_ref: str,
    plan: dict,
    strategy: dict,
    issues: list[dict[str, str]],
) -> None:
    required_fields = ("plan_id", "status", "strategy_ref", "basis", "execution_gate")
    missing = [field for field in required_fields if field not in plan]
    if missing:
        _add_issue(
            issues,
            "error",
            "active_plan_fields_missing",
            f"{plan_ref} is missing fields: {', '.join(missing)}",
        )
        return
    try:
        plan_strategy_path = resolve_repository_path(
            root,
            plan.get("strategy_ref"),
            field=f"{plan_ref} strategy_ref",
        )
        plan_strategy = load_yaml(plan_strategy_path)
    except Exception as exc:  # noqa: BLE001
        _add_issue(
            issues,
            "error",
            "active_plan_strategy_ref_invalid",
            str(exc),
        )
        plan_strategy = {}
    if plan_strategy.get("strategy_id") != strategy.get("strategy_id"):
        _add_issue(
            issues,
            "error",
            "active_plan_strategy_mismatch",
            f"{plan_ref} does not reference the active strategy version.",
        )
    _audit_reference(
        root,
        plan.get("basis", {}).get("snapshot_ref"),
        issues,
        code="active_plan_snapshot_ref_invalid",
        required=True,
    )
    if plan.get("execution_gate", {}).get("requires_user_confirmation") is not True:
        _add_issue(
            issues,
            "error",
            "active_plan_human_gate_missing",
            f"{plan_ref} must require user confirmation.",
        )


def _audit_snapshots(root: Path, issues: list[dict[str, str]]) -> None:
    snapshot_paths = sorted((root / "data/normalized").glob("snapshot_20??_??.yaml"))
    if not snapshot_paths:
        _add_issue(
            issues,
            "error",
            "normalized_snapshot_missing",
            "No dated normalized snapshots were found.",
        )
        return
    seen_dates: set[str] = set()
    for path in snapshot_paths:
        try:
            snapshot = load_snapshot(path)
        except Exception as exc:  # noqa: BLE001
            _add_issue(
                issues,
                "error",
                "normalized_snapshot_invalid",
                f"{path.relative_to(root)}: {exc}",
            )
            continue
        snapshot_date = snapshot.snapshot_date.isoformat()
        if snapshot_date in seen_dates:
            _add_issue(
                issues,
                "error",
                "duplicate_snapshot_date",
                f"More than one normalized snapshot uses {snapshot_date}.",
            )
        seen_dates.add(snapshot_date)


def _audit_raw_index(root: Path, issues: list[dict[str, str]]) -> None:
    index_path = root / "data/raw/index.yaml"
    if not index_path.exists():
        return
    index = load_yaml(index_path)
    for entry in index.get("entries", []):
        _audit_reference(
            root,
            entry.get("normalized_snapshot_ref"),
            issues,
            code="raw_index_snapshot_ref_invalid",
            required=True,
        )


def _audit_transaction_ledger(root: Path, issues: list[dict[str, str]]) -> None:
    ledger_path = root / "transactions/ledger.yaml"
    if not ledger_path.exists():
        return
    ledger = load_yaml(ledger_path)
    transactions = ledger.get("transactions")
    if not isinstance(transactions, list):
        _add_issue(
            issues,
            "error",
            "transaction_ledger_not_list",
            "transactions/ledger.yaml transactions must be a list.",
        )
        return
    seen_ids: set[str] = set()
    required = {
        "transaction_id",
        "status",
        "transaction_type",
        "trade_date",
        "account",
        "currency",
        "source_evidence",
    }
    for transaction in transactions:
        if not isinstance(transaction, dict):
            _add_issue(
                issues,
                "error",
                "transaction_not_mapping",
                "Every confirmed transaction must be a mapping.",
            )
            continue
        missing = sorted(required - set(transaction))
        if missing:
            _add_issue(
                issues,
                "error",
                "transaction_fields_missing",
                f"Transaction is missing fields: {', '.join(missing)}",
            )
        transaction_id = str(transaction.get("transaction_id", ""))
        if transaction_id in seen_ids:
            _add_issue(
                issues,
                "error",
                "duplicate_transaction_id",
                f"Duplicate transaction_id: {transaction_id}",
            )
        seen_ids.add(transaction_id)
        if transaction.get("status") != "confirmed":
            _add_issue(
                issues,
                "error",
                "unconfirmed_transaction_in_ledger",
                f"{transaction_id or '<missing id>'} is not confirmed.",
            )


def _audit_retrospective_index(root: Path, issues: list[dict[str, str]]) -> None:
    index_path = root / "retrospectives/index.yaml"
    if not index_path.exists():
        return
    index = load_yaml(index_path)
    for entry in index.get("entries", []):
        for field in ("original_review_ref", "structured_review_ref"):
            ref = entry.get(field)
            if ref is not None:
                _audit_reference(
                    root,
                    ref,
                    issues,
                    code="retrospective_source_ref_invalid",
                    required=True,
                )


def _audit_thesis_index(root: Path, issues: list[dict[str, str]]) -> None:
    index_path = root / "strategy/theses/index.yaml"
    if not index_path.exists():
        _add_issue(
            issues,
            "error",
            "thesis_index_missing",
            "strategy/theses/index.yaml is missing.",
        )
        return
    index = load_yaml(index_path)
    for entry in index.get("entries", []):
        _audit_reference(
            root,
            entry.get("thesis_ref"),
            issues,
            code="thesis_index_ref_invalid",
            required=True,
        )


def _audit_legacy_markers(root: Path, issues: list[dict[str, str]]) -> None:
    expected = {
        "config/portfolio_policy.yaml": "legacy_runtime_fallback",
        "config/allocation_rules.yaml": "legacy_runtime_fallback",
        "config/buy_rules.yaml": "legacy_analytical_heuristic",
        "config/core_recurring_contributions.yaml": "legacy_compatibility_pointer",
    }
    for relative_path, expected_status in expected.items():
        payload = load_yaml(root / relative_path)
        if payload.get("policy_status") != expected_status:
            _add_issue(
                issues,
                "error",
                "legacy_marker_missing",
                f"{relative_path} must declare policy_status={expected_status}.",
            )


def _audit_output_routing(root: Path, issues: list[dict[str, str]]) -> None:
    monthly_paths = default_output_paths(root, "2099_01")
    on_demand_paths = on_demand_output_paths(root)
    for name, path in {**monthly_paths, **on_demand_paths}.items():
        if not path.resolve().is_relative_to((root / "reports/generated").resolve()):
            _add_issue(
                issues,
                "error",
                "generated_output_outside_reports",
                f"Generated output {name} is routed outside reports/generated: {path}",
            )


def _audit_reference(
    root: Path,
    ref,
    issues: list[dict[str, str]],
    *,
    code: str,
    required: bool,
) -> None:
    if ref in (None, ""):
        if required:
            _add_issue(issues, "error", code, "Required repository reference is missing.")
        return
    try:
        resolve_repository_path(root, str(ref), field=code)
    except RepositoryIntegrityError as exc:
        _add_issue(issues, "error", code, str(exc))


def _add_issue(
    issues: list[dict[str, str]],
    severity: str,
    code: str,
    message: str,
) -> None:
    issues.append({"severity": severity, "code": code, "message": message})
