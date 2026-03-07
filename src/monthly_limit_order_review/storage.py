from __future__ import annotations

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
    return {
        "computation": project_root / "data/history/computations" / f"{snapshot_month}_computation.yaml",
        "review_prompt": project_root / "prompts/generated" / f"monthly_review_prompt_{snapshot_month}.md",
        "review_prompt_history": project_root / "data/history/prompts" / f"{snapshot_month}_monthly_review_prompt.md",
        "review_structured": project_root / "data/history/reviews" / f"{snapshot_month}_review_structured.yaml",
        "diff": project_root / "data/history/diffs" / f"{snapshot_month}_python_vs_chatgpt.yaml",
        "patch_request": project_root
        / "data/history/codex_patch_requests"
        / f"{snapshot_month}_codex_patch_request.yaml",
        "patch_prompt": project_root / "prompts/generated" / f"codex_patch_prompt_{snapshot_month}.md",
    }

