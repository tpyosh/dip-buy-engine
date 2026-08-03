from __future__ import annotations

from datetime import date
from pathlib import Path

from .models import PortfolioSnapshot
from .storage import load_yaml


def load_financial_context(project_root: Path) -> dict:
    return _load_versioned_context(
        project_root,
        pointer_ref="financial/current.yaml",
        expected_record_type="personal_financial_context",
    )


def load_holding_metadata_context(project_root: Path) -> dict:
    return _load_versioned_context(
        project_root,
        pointer_ref="holdings/current.yaml",
        expected_record_type="holding_metadata",
    )


def apply_holding_metadata(
    snapshot: PortfolioSnapshot,
    holding_metadata_record: dict,
) -> None:
    effective_from = holding_metadata_record.get("effective_from")
    if effective_from and date.fromisoformat(str(effective_from)) > snapshot.snapshot_date:
        return
    metadata_by_symbol = holding_metadata_record.get("holdings", {})
    for holding in snapshot.holdings:
        metadata = metadata_by_symbol.get(holding.symbol)
        if not isinstance(metadata, dict):
            continue
        account = metadata.get("account", {})
        confirmed_account_type = account.get("account_type")
        if confirmed_account_type:
            holding.account_type = str(confirmed_account_type)


def holding_metadata_by_symbol(context: dict) -> dict[str, dict]:
    record = context.get("record", {})
    holdings = record.get("holdings", {})
    return holdings if isinstance(holdings, dict) else {}


def _load_versioned_context(
    project_root: Path,
    *,
    pointer_ref: str,
    expected_record_type: str,
) -> dict:
    root = project_root.resolve()
    pointer_path = root / pointer_ref
    pointer = load_yaml(pointer_path)
    record_ref = pointer.get("active_record_path")
    if not record_ref:
        raise ValueError(f"{pointer_ref} must define active_record_path")
    record_path = (root / str(record_ref)).resolve()
    if not record_path.is_relative_to(root):
        raise ValueError(f"{pointer_ref} active_record_path must stay in repository")
    record = load_yaml(record_path)
    if record.get("record_type") != expected_record_type:
        raise ValueError(
            f"{record_ref} record_type must be {expected_record_type}"
        )
    if pointer.get("active_record_id") != record.get("record_id"):
        raise ValueError(f"{pointer_ref} active_record_id does not match {record_ref}")
    return {
        "pointer": pointer,
        "record": record,
        "source_path": str(record_path.relative_to(root)),
    }
