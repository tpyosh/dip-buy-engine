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


def test_load_snapshot_reads_ocr_metadata_fields(tmp_path: Path) -> None:
    path = tmp_path / "snapshot_with_ocr_metadata.yaml"
    path.write_text(
        """snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 1000000
category_totals_jpy:
  core: 1000000
source_evidence:
  primary_source: "moneyforward_screenshots"
ocr_notes:
  - "one field was unreadable"
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
    notes: "OCR confidence low"
""",
        encoding="utf-8",
    )

    snapshot = load_snapshot(path)
    holding = snapshot.holdings[0]

    assert snapshot.category_totals_jpy["core"] == 1000000
    assert snapshot.source_evidence["primary_source"] == "moneyforward_screenshots"
    assert snapshot.ocr_notes == ["one field was unreadable"]
    assert snapshot.validation_notes == ["checked totals"]
    assert holding.source_category == "投資信託"
    assert holding.institution == "Test Securities"
    assert holding.account_type == "NISAつみたて投資枠"
    assert holding.unit_price == 1000
    assert holding.profit_loss_jpy == 100000
    assert holding.valuation_jpy == 1000000
    assert holding.notes == "OCR confidence low"
