from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


def test_total_assets_gap_below_point_one_percent_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "snapshot_relative_tolerance.yaml"
    path.write_text(
        """snapshot_date: "2026-08-09"
currency_base: "JPY"
total_assets_jpy: 40000000
holdings:
  - symbol: "TEST"
    name: "Test Asset"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 39960001
    currency: "JPY"
""",
        encoding="utf-8",
    )

    snapshot = load_snapshot(path)

    assert not any("Sum of holding market values" in warning for warning in snapshot.warnings)


def test_total_assets_gap_at_point_one_percent_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "snapshot_relative_tolerance_boundary.yaml"
    path.write_text(
        """snapshot_date: "2026-08-09"
currency_base: "JPY"
total_assets_jpy: 40000000
holdings:
  - symbol: "TEST"
    name: "Test Asset"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 39960000
    currency: "JPY"
""",
        encoding="utf-8",
    )

    snapshot = load_snapshot(path)

    assert any("Sum of holding market values" in warning for warning in snapshot.warnings)


def test_load_snapshot_reads_normalization_metadata_fields(tmp_path: Path) -> None:
    path = tmp_path / "snapshot_with_normalization_metadata.yaml"
    path.write_text(
        """snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 1000000
category_totals_jpy:
  core: 1000000
source_evidence:
  primary_source: "broker_csv"
normalization_notes:
  - "one field was missing"
validation_notes:
  - "checked totals"
holdings:
  - symbol: "TEST"
    name: "Test Asset"
    source_category: "投資信託"
    institution: "Test Securities"
    account_type: "NISAつみたて投資枠"
    asset_class: "core"
    quantity: 10
    avg_cost: 900
    current_price: 1000
    unit_price: 1000
    profit_loss_jpy: 100000
    valuation_jpy: 1000000
    market_value_jpy: 1000000
    currency: "JPY"
    notes: "Source field missing"
""",
        encoding="utf-8",
    )

    snapshot = load_snapshot(path)
    holding = snapshot.holdings[0]

    assert snapshot.category_totals_jpy["core"] == 1000000
    assert snapshot.source_evidence["primary_source"] == "broker_csv"
    assert snapshot.normalization_notes == ["one field was missing"]
    assert snapshot.validation_notes == ["checked totals"]
    assert holding.source_category == "投資信託"
    assert holding.institution == "Test Securities"
    assert holding.account_type == "NISAつみたて投資枠"
    assert holding.unit_price == 1000
    assert holding.profit_loss_jpy == 100000
    assert holding.valuation_jpy == 1000000
    assert holding.notes == "Source field missing"


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({"ocr_notes": ["legacy source uncertainty"]}, ["legacy source uncertainty"]),
        (
            {
                "normalization_notes": ["new source uncertainty", "shared note"],
                "ocr_notes": ["legacy source uncertainty", "shared note"],
            },
            ["new source uncertainty", "shared note", "legacy source uncertainty"],
        ),
    ],
)
def test_load_snapshot_preserves_legacy_notes(
    tmp_path: Path, sample_snapshot_path: Path, metadata: dict, expected: list[str]
) -> None:
    payload = yaml.safe_load(sample_snapshot_path.read_text(encoding="utf-8"))
    payload.pop("normalization_notes", None)
    payload.update(metadata)
    path = tmp_path / "legacy_notes.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    assert load_snapshot(path).normalization_notes == expected
