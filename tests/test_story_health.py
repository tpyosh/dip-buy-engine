from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.repository_records import load_thesis_monitoring_policy
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.story_health import build_security_story_targets


ROOT = Path(__file__).resolve().parents[1]


def test_story_targets_cover_every_held_individual_stock_and_etf() -> None:
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")
    policy = load_thesis_monitoring_policy(ROOT)

    targets = build_security_story_targets(snapshot, policy)
    by_symbol = {target["symbol"]: target for target in targets}

    assert set(by_symbol) == {
        "7203",
        "9444",
        "2353",
        "7201",
        "SMH",
        "PLTR",
        "CIBR",
        "MSFT",
        "URA",
    }
    assert by_symbol["SMH"]["instrument_type"] == "etf"
    assert by_symbol["SMH"]["thesis_status"] == "active"
    assert by_symbol["7203"]["thesis_recorded"] is False
    assert by_symbol["7203"]["thesis_status"] == "missing"
    assert "暫定ストーリー" in by_symbol["7203"]["required_assessment"]
