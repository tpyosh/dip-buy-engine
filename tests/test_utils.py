from __future__ import annotations

from datetime import date
from pathlib import Path

from monthly_limit_order_review.utils import infer_target_month_start, target_month_key


def test_target_month_key_prefers_snapshot_filename_month() -> None:
    key = target_month_key(
        date(2026, 3, 29),
        snapshot_path=Path("/tmp/data/normalized/snapshot_2026_04.yaml"),
    )

    assert key == "2026_04"


def test_target_month_key_rolls_month_end_forward_without_filename_hint() -> None:
    month_start = infer_target_month_start(date(2026, 3, 29))

    assert month_start == date(2026, 4, 1)


def test_target_month_key_keeps_early_month_in_same_month() -> None:
    key = target_month_key(date(2026, 4, 2))

    assert key == "2026_04"
