from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .utils import ensure_parent, to_serializable


def load_yaml(path: str | Path) -> dict:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"YAML file must contain a mapping: {path}")
    return payload


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, content: str) -> Path:
    output_path = Path(path)
    ensure_parent(output_path)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def write_yaml(path: str | Path, data: Any) -> Path:
    output_path = Path(path)
    ensure_parent(output_path)
    output_path.write_text(
        yaml.safe_dump(
            to_serializable(data),
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return output_path


def default_output_paths(project_root: Path, snapshot_month: str) -> dict[str, Path]:
    output_root = project_root / "reports/generated/monthly" / snapshot_month
    return {
        "output_root": output_root,
        "computation": output_root / "computation.yaml",
        "review_packet": output_root / "review_packet.yaml",
        "review_prompt": output_root / "review_request.md",
        "review_prompt_history": output_root / "review_request.md",
        "review_structured": output_root / "review_response.yaml",
        "diff": output_root / "proposal_diff.yaml",
        "calendar_events": output_root / "calendar_events.yaml",
        "patch_request": output_root / "codex_patch_request.yaml",
        "patch_prompt": output_root / "codex_patch_request.md",
    }


def on_demand_output_paths(
    project_root: Path,
    requested_at: datetime | None = None,
) -> dict[str, Path]:
    current = requested_at or datetime.now(UTC)
    timestamp = current.astimezone(UTC).strftime("%Y_%m_%dT%H%M%SZ")
    output_root = (
        project_root
        / "reports/generated/on_demand"
        / current.astimezone(UTC).strftime("%Y")
        / timestamp
    )
    return {
        "output_root": output_root,
        "market_data": output_root / "market_data.yaml",
        "prompt": output_root / "health_check_request.md",
        "prompt_history": output_root / "health_check_request.md",
        "response": output_root / "health_check_response.yaml",
    }
