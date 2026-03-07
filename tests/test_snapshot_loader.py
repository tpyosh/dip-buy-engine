from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.snapshot_loader import load_snapshot


def test_load_snapshot_reads_yaml(sample_snapshot_path: Path) -> None:
    snapshot = load_snapshot(sample_snapshot_path)

    assert snapshot.snapshot_date.isoformat() == "2026-03-07"
    assert snapshot.currency_base == "JPY"
    assert len(snapshot.holdings) == 6
    assert snapshot.total_assets_jpy == 5000000


def test_load_snapshot_warns_on_missing_optional_fields(tmp_path: Path) -> None:
    path = tmp_path / "snapshot_missing.yaml"
    path.write_text(
        """snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 1000000
holdings:
  - symbol: "TEST"
    name: "Test Asset"
    market_value_jpy: 1000000
    currency: "JPY"
""",
        encoding="utf-8",
    )

    snapshot = load_snapshot(path)

    assert any("asset_class" in warning for warning in snapshot.warnings)
    assert any("quantity" in warning for warning in snapshot.warnings)


def test_small_total_assets_gap_is_tolerated(tmp_path: Path) -> None:
    path = tmp_path / "snapshot_tolerance.yaml"
    path.write_text(
        """snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 1000002
holdings:
  - symbol: "TEST"
    name: "Test Asset"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 1000000
    currency: "JPY"
""",
        encoding="utf-8",
    )

    snapshot = load_snapshot(path)

    assert not any("Sum of holding market values" in warning for warning in snapshot.warnings)
