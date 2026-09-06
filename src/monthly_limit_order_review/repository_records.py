from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .context_records import load_financial_context, load_holding_metadata_context
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
        symbols = thesis.get("covered_symbols") or [thesis.get("symbol")]
        symbols = [str(symbol) for symbol in symbols if symbol not in (None, "")]
        if not symbols:
            continue
        summary = thesis.get("legacy_summary")
        if summary is None:
            summary = " ".join(thesis.get("claims", {}).get("supported", [])) or None
        break_conditions = thesis.get("legacy_break_conditions")
        if break_conditions is None:
            break_conditions = thesis.get("invalidation_or_reduction_review", [])
        for symbol in symbols:
            policy[symbol] = {
                "enabled": True,
                "thesis_id": thesis.get("thesis_id"),
                "thesis_status": entry.get("status") or thesis.get("status"),
                "long_term_thesis_summary": summary,
                "key_risk_if_thesis_breaks": break_conditions,
                "review_priority": priorities.get(symbol, "medium"),
                "instrument_type": thesis.get("instrument_type"),
                "thesis_source_ref": entry.get("thesis_ref"),
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
        "financial/current.yaml",
        "holdings/current.yaml",
        "strategy/current.yaml",
        "plans/README.md",
        "plans/recurring/current.yaml",
        "transactions/ledger.yaml",
        "brokers/README.md",
        "brokers/rakuten/us_equity_sell/current.yaml",
        "retrospectives/index.yaml",
        "reports/legacy-index.yaml",
        "data/raw/index.yaml",
        "schemas/snapshot.schema.yaml",
        "schemas/strategy.schema.yaml",
        "schemas/plan.schema.yaml",
        "schemas/transaction.schema.yaml",
        "schemas/annual-tax-record.schema.yaml",
        "schemas/broker-order-capability.schema.yaml",
        "schemas/retrospective.schema.yaml",
        "schemas/review-packet.schema.yaml",
        "schemas/monthly-review-response.schema.yaml",
        "schemas/health-check-response.schema.yaml",
        "schemas/financial-context.schema.yaml",
        "schemas/holding-metadata.schema.yaml",
        "schemas/independent-decision-request.schema.yaml",
        "schemas/independent-decision-response.schema.yaml",
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

    for plan_path in sorted((root / "plans").glob("20??/*.yaml")):
        plan_ref = str(plan_path.relative_to(root))
        try:
            plan = load_yaml(plan_path)
        except Exception as exc:  # noqa: BLE001
            _add_issue(
                issues,
                "error",
                "task_plan_invalid",
                f"{plan_ref}: {exc}",
            )
            continue
        _audit_task_execution_contract(plan_ref, plan, issues, root=root)

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

    for loader, code in (
        (load_financial_context, "financial_context_invalid"),
        (load_holding_metadata_context, "holding_metadata_invalid"),
    ):
        try:
            loader(root)
        except Exception as exc:  # noqa: BLE001
            _add_issue(issues, "error", code, str(exc))

    if strategy_context:
        try:
            financial_context = load_financial_context(root)
        except Exception:  # already reported above
            financial_context = {}
        if financial_context:
            _audit_financial_unknowns_against_strategy(
                financial_context["record"],
                strategy_context["strategy"],
                issues,
            )

    _audit_snapshots(root, issues)
    _audit_normalized_snapshot_pointer(root, issues)
    _audit_raw_index(root, issues)
    _audit_transaction_ledger(root, issues)
    _audit_broker_capability_pointers(root, issues)
    _audit_retrospective_index(root, issues)
    _audit_thesis_index(root, issues)
    _audit_legacy_markers(root, issues)
    _audit_output_routing(root, issues)
    return issues


def _audit_financial_unknowns_against_strategy(
    financial_record: dict,
    strategy: dict,
    issues: list[dict[str, str]],
) -> None:
    if strategy.get("allocation", {}).get("status") != "approved":
        return
    unknowns = [str(item) for item in financial_record.get("unknown_information", [])]
    stale = [
        item
        for item in unknowns
        if item.startswith("投資待機資金")
        or item.startswith("サテライトの目標比率")
    ]
    if stale:
        _add_issue(
            issues,
            "error",
            "financial_unknowns_conflict_with_approved_strategy",
            "financial/current.yaml still marks approved investment-policy fields as unknown: "
            + "; ".join(stale),
        )


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


def _audit_task_execution_contract(
    plan_ref: str,
    plan: dict,
    issues: list[dict[str, str]],
    *,
    root: Path | None = None,
) -> None:
    """Require source-aware inputs, allocation denominators, and order settings."""

    tasks = plan.get("tasks")
    if tasks is None:
        return
    if not isinstance(tasks, list) or not tasks:
        _add_issue(
            issues,
            "error",
            "task_plan_tasks_invalid",
            f"{plan_ref} tasks must be a non-empty list.",
        )
        return

    task_ids: list[str] = []
    for index, task in enumerate(tasks, start=1):
        if not isinstance(task, dict):
            _add_issue(
                issues,
                "error",
                "task_plan_task_invalid",
                f"{plan_ref} task #{index} must be an object.",
            )
            continue
        task_id = str(task.get("id") or f"task#{index}")
        task_ids.append(task_id)
        missing_core = [
            field
            for field in (
                "id",
                "status",
                "action",
                "action_kind",
                "allocation_effect",
                "human_actionability",
            )
            if task.get(field) in (None, "")
        ]
        if missing_core:
            _add_issue(
                issues,
                "error",
                "task_plan_core_fields_missing",
                f"{plan_ref} {task_id} is missing: {', '.join(missing_core)}.",
            )
            continue

        if task.get("action_kind") == "hold":
            _add_issue(
                issues,
                "error",
                "task_prohibition_only_control_invalid",
                f"{plan_ref} {task_id} uses action_kind hold. Prohibitions and "
                "no-action controls must be represented in execution_guardrails, not tasks.",
            )

        actionability = task.get("human_actionability")
        required_actionability = (
            "actor",
            "next_action",
            "required_inputs",
            "decision_needed",
            "decision_support_owner",
            "unblock_condition",
            "completion_evidence",
        )
        if not isinstance(actionability, dict):
            missing_actionability = list(required_actionability)
        else:
            missing_actionability = [
                field for field in required_actionability if field not in actionability
            ]
        if missing_actionability:
            _add_issue(
                issues,
                "error",
                "task_human_actionability_missing",
                f"{plan_ref} {task_id} human actionability is missing: "
                f"{', '.join(missing_actionability)}.",
            )
        elif not actionability.get("next_action") or not actionability.get("unblock_condition"):
            _add_issue(
                issues,
                "error",
                "task_human_actionability_empty",
                f"{plan_ref} {task_id} must state the next action and unblock condition.",
            )
        elif actionability.get("actor") not in {
            "user",
            "codex",
            "external_broker",
            "codex_and_user",
            "user_and_external_broker",
        }:
            _add_issue(
                issues,
                "error",
                "task_actionability_actor_invalid",
                f"{plan_ref} {task_id} has an invalid next actor.",
            )
        elif not isinstance(actionability.get("required_inputs"), list):
            _add_issue(
                issues,
                "error",
                "task_required_inputs_invalid",
                f"{plan_ref} {task_id} required_inputs must be a list.",
            )
        elif not _audit_task_input_resolution(
            plan_ref,
            task_id,
            actionability.get("required_inputs", []),
            issues,
            root=root,
        ):
            pass
        elif not isinstance(actionability.get("completion_evidence"), list) or not actionability.get("completion_evidence"):
            _add_issue(
                issues,
                "error",
                "task_completion_evidence_missing",
                f"{plan_ref} {task_id} must state completion evidence.",
            )
        elif actionability.get("decision_needed") and not actionability.get("decision_support_owner"):
            _add_issue(
                issues,
                "error",
                "task_decision_support_owner_missing",
                f"{plan_ref} {task_id} must identify who prepares decision support.",
            )

        allocation_effect = task.get("allocation_effect")
        if allocation_effect in {"target_ratio", "ratio_cap", "ratio_range", "target_mix"}:
            basis = task.get("allocation_basis")
            required_basis = (
                "denominator",
                "denominator_definition_ref",
                "measurement_time",
                "targets",
            )
            if not isinstance(basis, dict):
                missing_basis = list(required_basis)
            else:
                missing_basis = [
                    field
                    for field in required_basis
                    if basis.get(field) in (None, "", [])
                ]
            if missing_basis:
                _add_issue(
                    issues,
                    "error",
                    "task_allocation_basis_missing",
                    f"{plan_ref} {task_id} allocation target is missing: "
                    f"{', '.join(missing_basis)}.",
                )

        if task.get("action_kind") not in {"buy", "sell"}:
            continue
        order = task.get("order_specification")
        required_order = (
            "status",
            "execution_allowed",
            "account_type",
            "side",
            "quantity_rule",
            "order_type",
            "limit_price_rule",
            "timing",
            "expiration",
            "partial_fill_handling",
            "unfilled_or_expired_reorder_rule",
            "proceeds_destination",
            "pretrade_tax_check",
            "user_approval_required",
            "user_approval_status",
        )
        if not isinstance(order, dict):
            missing_order = list(required_order)
        else:
            missing_order = [field for field in required_order if field not in order]
        if missing_order:
            _add_issue(
                issues,
                "error",
                "task_order_specification_missing",
                f"{plan_ref} {task_id} order specification is missing: "
                f"{', '.join(missing_order)}.",
            )
            continue
        if order.get("user_approval_required") is not True:
            _add_issue(
                issues,
                "error",
                "task_order_user_approval_missing",
                f"{plan_ref} {task_id} must require user approval.",
            )
        if order.get("user_approval_status") not in {
            "pending",
            "approved",
            "approved_existing_order",
        }:
            _add_issue(
                issues,
                "error",
                "task_order_user_approval_status_invalid",
                f"{plan_ref} {task_id} has an invalid user approval status.",
            )
        if order.get("status") != "configured" and order.get("execution_allowed") is not False:
            _add_issue(
                issues,
                "error",
                "task_order_pending_but_executable",
                f"{plan_ref} {task_id} cannot be executable before its order settings are configured.",
            )
        if order.get("execution_allowed") is True and order.get("user_approval_status") != "approved":
            _add_issue(
                issues,
                "error",
                "task_order_executable_without_approval",
                f"{plan_ref} {task_id} cannot be executable without current user approval.",
            )
        if order.get("status") == "configured" and order.get("order_type") in {
            "pending_user_approval",
            "existing_order_type_unconfirmed",
        }:
            _add_issue(
                issues,
                "error",
                "task_order_configured_with_pending_type",
                f"{plan_ref} {task_id} is configured but has no concrete order type.",
            )
        if order.get("order_type") == "limit" and not order.get("limit_price_rule"):
            _add_issue(
                issues,
                "error",
                "task_limit_price_rule_missing",
                f"{plan_ref} {task_id} limit order must define limit_price_rule.",
            )

    duplicates = sorted({task_id for task_id in task_ids if task_ids.count(task_id) > 1})
    if duplicates:
        _add_issue(
            issues,
            "error",
            "task_plan_duplicate_ids",
            f"{plan_ref} has duplicate task ids: {', '.join(duplicates)}.",
        )


def _audit_task_input_resolution(
    plan_ref: str,
    task_id: str,
    inputs: list,
    issues: list[dict[str, str]],
    *,
    root: Path | None,
) -> bool:
    """Reject user-input lists that do not resolve repository evidence first."""

    valid = True
    required_fields = {
        "key",
        "label",
        "availability",
        "source_ref",
        "value_summary",
        "as_of",
        "refresh_rule",
        "request_from_user_if",
        "blocking",
        "owner",
        "verification_stage",
        "trigger_evidence",
        "scope",
    }
    allowed_availability = {
        "resolved_from_repository",
        "known_event_pending",
        "refresh_by_codex",
        "verify_at_execution",
        "user_input_blocking",
    }
    allowed_owners = {
        "codex",
        "user",
        "external_broker",
        "codex_and_user",
        "user_and_external_broker",
    }
    allowed_stages = {
        "draft",
        "approval",
        "order_entry",
        "settlement",
        "post_trade",
        "continuous",
    }
    keys: list[str] = []
    for index, item in enumerate(inputs, start=1):
        if not isinstance(item, dict):
            _add_issue(
                issues,
                "error",
                "task_input_resolution_unstructured",
                f"{plan_ref} {task_id} required input #{index} must be source-aware.",
            )
            valid = False
            continue
        missing = sorted(required_fields - set(item))
        if missing:
            _add_issue(
                issues,
                "error",
                "task_input_resolution_fields_missing",
                f"{plan_ref} {task_id} required input #{index} is missing: "
                f"{', '.join(missing)}.",
            )
            valid = False
            continue
        key = item.get("key")
        if not isinstance(key, str) or not key:
            _add_issue(
                issues,
                "error",
                "task_input_resolution_key_invalid",
                f"{plan_ref} {task_id} required input #{index} needs a key.",
            )
            valid = False
        else:
            keys.append(key)
        availability = item.get("availability")
        if availability not in allowed_availability:
            _add_issue(
                issues,
                "error",
                "task_input_resolution_availability_invalid",
                f"{plan_ref} {task_id} required input #{index} has invalid availability.",
            )
            valid = False
            continue
        source_ref = item.get("source_ref")
        as_of = item.get("as_of")
        refresh_rule = item.get("refresh_rule")
        user_condition = item.get("request_from_user_if")
        blocking = item.get("blocking")
        owner = item.get("owner")
        stage = item.get("verification_stage")
        trigger = item.get("trigger_evidence")
        scope = item.get("scope")
        if owner not in allowed_owners or stage not in allowed_stages or not scope:
            _add_issue(
                issues,
                "error",
                "task_input_execution_context_invalid",
                f"{plan_ref} {task_id} required input #{index} must state a valid "
                "owner, verification_stage, and scope.",
            )
            valid = False
        if availability == "resolved_from_repository":
            if (
                not source_ref
                or not as_of
                or user_condition is not None
                or blocking is not False
            ):
                _add_issue(
                    issues,
                    "error",
                    "task_repository_input_contract_invalid",
                    f"{plan_ref} {task_id} repository-resolved input #{index} "
                    "must have source_ref/as_of, be non-blocking, and must not "
                    "request user resubmission.",
                )
                valid = False
        elif availability == "known_event_pending":
            if not source_ref or not as_of or not refresh_rule or not trigger:
                _add_issue(
                    issues,
                    "error",
                    "task_known_event_contract_invalid",
                    f"{plan_ref} {task_id} known event #{index} must state its source, "
                    "basis time, refresh rule, and trigger evidence.",
                )
                valid = False
        elif availability == "refresh_by_codex":
            if not refresh_rule or user_condition is not None or owner != "codex":
                _add_issue(
                    issues,
                    "error",
                    "task_codex_refresh_contract_invalid",
                    f"{plan_ref} {task_id} Codex refresh #{index} must have a refresh "
                    "rule, Codex owner, and no user request.",
                )
                valid = False
        elif availability == "verify_at_execution":
            if (
                not refresh_rule
                or user_condition is not None
                or blocking is not False
                or stage != "order_entry"
                or not trigger
            ):
                _add_issue(
                    issues,
                    "error",
                    "task_execution_preflight_contract_invalid",
                    f"{plan_ref} {task_id} execution preflight #{index} must be "
                    "non-blocking for draft, occur at order_entry, and have a trigger.",
                )
                valid = False
        elif availability == "user_input_blocking":
            if (
                source_ref is not None
                or as_of is not None
                or not user_condition
                or blocking is not True
                or not trigger
            ):
                _add_issue(
                    issues,
                    "error",
                    "task_blocking_user_input_contract_invalid",
                    f"{plan_ref} {task_id} blocking user input #{index} must have "
                    "no repository source, be blocking, and state its trigger and request.",
                )
                valid = False
        if root is not None and source_ref:
            try:
                resolve_repository_path(
                    root,
                    str(source_ref).split("#", 1)[0],
                    field=f"{plan_ref} {task_id} required input #{index} source_ref",
                )
            except Exception as exc:  # noqa: BLE001
                _add_issue(
                    issues,
                    "error",
                    "task_input_source_ref_invalid",
                    str(exc),
                )
                valid = False
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        _add_issue(
            issues,
            "error",
            "task_input_resolution_duplicate_keys",
            f"{plan_ref} {task_id} has duplicate required input keys: "
            f"{', '.join(duplicates)}.",
        )
        valid = False
    return valid


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
        partial_refs = entry.get("partial_evidence_refs", [])
        if not isinstance(partial_refs, list):
            _add_issue(
                issues,
                "error",
                "raw_index_partial_evidence_refs_invalid",
                "data/raw/index.yaml partial_evidence_refs must be a list.",
            )
            continue
        for evidence_ref in partial_refs:
            _audit_reference(
                root,
                evidence_ref,
                issues,
                code="raw_index_partial_evidence_ref_invalid",
                required=True,
            )


def _audit_normalized_snapshot_pointer(
    root: Path,
    issues: list[dict[str, str]],
) -> None:
    pointer_path = root / "data/normalized/current.yaml"
    if not pointer_path.exists():
        _add_issue(
            issues,
            "error",
            "normalized_snapshot_pointer_missing",
            "data/normalized/current.yaml is required.",
        )
        return
    pointer = load_yaml(pointer_path)
    active_ref = pointer.get("active_snapshot_path")
    _audit_reference(
        root,
        active_ref,
        issues,
        code="normalized_snapshot_pointer_ref_invalid",
        required=True,
    )
    if not active_ref:
        return
    try:
        snapshot = load_snapshot(resolve_repository_path(
            root,
            active_ref,
            field="data/normalized/current.yaml active_snapshot_path",
        ))
    except Exception:
        return
    if pointer.get("active_snapshot_date") != snapshot.snapshot_date.isoformat():
        _add_issue(
            issues,
            "error",
            "normalized_snapshot_pointer_date_mismatch",
            "data/normalized/current.yaml active_snapshot_date does not match its snapshot.",
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
    annual_records: dict[str, dict] = {}
    annual_transaction_refs: dict[str, tuple[str, dict]] = {}
    tax_dir = root / "transactions/tax"
    for annual_path in sorted(tax_dir.glob("[0-9][0-9][0-9][0-9].yaml")):
        annual_ref = str(annual_path.relative_to(root))
        try:
            annual_record = load_yaml(annual_path)
        except Exception as exc:  # noqa: BLE001
            _add_issue(
                issues,
                "error",
                "annual_tax_record_invalid",
                f"{annual_ref}: {exc}",
            )
            continue
        annual_records[annual_ref] = annual_record
        expected_year = int(annual_path.stem)
        if annual_record.get("record_type") != "annual_tax_reconciliation":
            _add_issue(
                issues,
                "error",
                "annual_tax_record_type_invalid",
                f"{annual_ref} must be an annual_tax_reconciliation record.",
            )
        if annual_record.get("tax_year") != expected_year:
            _add_issue(
                issues,
                "error",
                "annual_tax_year_mismatch",
                f"{annual_ref} tax_year must match its filename.",
            )
        sales = annual_record.get("sales")
        if not isinstance(sales, list):
            _add_issue(
                issues,
                "error",
                "annual_tax_sales_not_list",
                f"{annual_ref} sales must be a list.",
            )
            continue
        for sale in sales:
            if not isinstance(sale, dict) or not sale.get("transaction_ref"):
                _add_issue(
                    issues,
                    "error",
                    "annual_tax_sale_invalid",
                    f"{annual_ref} contains a sale without transaction_ref.",
                )
                continue
            transaction_ref = str(sale["transaction_ref"])
            if transaction_ref in annual_transaction_refs:
                _add_issue(
                    issues,
                    "error",
                    "annual_tax_transaction_duplicate",
                    f"Annual tax records contain duplicate transaction_ref: {transaction_ref}",
                )
                continue
            annual_transaction_refs[transaction_ref] = (annual_ref, sale)
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
        if transaction.get("transaction_type") != "sell":
            continue
        tax_record = transaction.get("tax_record")
        if not isinstance(tax_record, dict):
            _add_issue(
                issues,
                "error",
                "sale_tax_record_missing",
                f"{transaction_id or '<missing id>'} must have tax_record.",
            )
            continue
        annual_ref = tax_record.get("annual_record_ref")
        if annual_ref not in annual_records:
            _add_issue(
                issues,
                "error",
                "sale_annual_tax_record_ref_invalid",
                f"{transaction_id or '<missing id>'} references missing annual tax record: {annual_ref}",
            )
            continue
        transaction_ref = f"transactions/ledger.yaml#{transaction_id}"
        annual_entry = annual_transaction_refs.get(transaction_ref)
        if annual_entry is None or annual_entry[0] != annual_ref:
            _add_issue(
                issues,
                "error",
                "sale_missing_from_annual_tax_record",
                f"{transaction_id or '<missing id>'} is not indexed by {annual_ref}.",
            )
            continue
        annual_sale = annual_entry[1]
        for field in ("status", "filing_category", "missing_fields"):
            if tax_record.get(field) != annual_sale.get(field):
                _add_issue(
                    issues,
                    "error",
                    "sale_annual_tax_record_mismatch",
                    f"{transaction_id or '<missing id>'} {field} differs between ledger and {annual_ref}.",
                )
        if tax_record.get("status") in {
            "reconciled_to_annual_statement",
            "non_taxable_reconciled",
        }:
            if tax_record.get("missing_fields"):
                _add_issue(
                    issues,
                    "error",
                    "reconciled_sale_has_missing_tax_fields",
                    f"{transaction_id or '<missing id>'} is reconciled but still has missing_fields.",
                )
            if not tax_record.get("annual_statement_evidence_ref"):
                _add_issue(
                    issues,
                    "error",
                    "reconciled_sale_evidence_missing",
                    f"{transaction_id or '<missing id>'} is reconciled without annual statement evidence.",
                )

    known_transaction_refs = {
        f"transactions/ledger.yaml#{transaction_id}" for transaction_id in seen_ids
    }
    for transaction_ref, (annual_ref, _) in annual_transaction_refs.items():
        if transaction_ref not in known_transaction_refs:
            _add_issue(
                issues,
                "error",
                "annual_tax_transaction_ref_unknown",
                f"{annual_ref} references unknown transaction: {transaction_ref}",
            )


def _audit_broker_capability_pointers(
    root: Path,
    issues: list[dict[str, str]],
) -> None:
    brokers_root = root / "brokers"
    if not brokers_root.exists():
        return
    for pointer_path in sorted(brokers_root.rglob("current.yaml")):
        pointer_ref = str(pointer_path.relative_to(root))
        try:
            pointer = load_yaml(pointer_path)
            capability_path = resolve_repository_path(
                root,
                pointer.get("active_capability_path"),
                field=f"{pointer_ref} active_capability_path",
            )
            capability = load_yaml(capability_path)
        except Exception as exc:  # noqa: BLE001
            _add_issue(
                issues,
                "error",
                "broker_capability_pointer_invalid",
                str(exc),
            )
            continue
        if pointer.get("active_capability_id") != capability.get("capability_id"):
            _add_issue(
                issues,
                "error",
                "broker_capability_id_mismatch",
                f"{pointer_ref} active_capability_id does not match its record.",
            )
        evidence_ref = capability.get("evidence_ref")
        try:
            resolve_repository_path(
                root,
                evidence_ref,
                field=f"{capability_path.relative_to(root)} evidence_ref",
            )
        except Exception as exc:  # noqa: BLE001
            _add_issue(
                issues,
                "error",
                "broker_capability_evidence_invalid",
                str(exc),
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
