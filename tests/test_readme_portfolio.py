from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from monthly_limit_order_review.models import BucketAllocation
from monthly_limit_order_review.readme_portfolio import (
    build_bucket_summary,
    build_bucket_summary_table,
    build_portfolio_pie_svg,
    build_readme_image_markdown,
    refresh_readme_portfolio,
    update_readme_portfolio_section,
)


def make_allocation(bucket: str, market_value: str, pct: str) -> BucketAllocation:
    return BucketAllocation(
        bucket=bucket,
        market_value_jpy=Decimal(market_value),
        actual_pct=Decimal(pct),
        target_pct=None,
        delta_pct=None,
        preferred_min_pct=None,
        preferred_max_pct=None,
    )


def test_bucket_summary_aggregates_in_fixed_order() -> None:
    allocations = [
        make_allocation("liquidity", "1200000", "0.2400"),
        make_allocation("core", "1800000", "0.3600"),
        make_allocation("jun_core", "800000", "0.1600"),
        make_allocation("satellite_core", "800000", "0.1600"),
        make_allocation("satellite", "400000", "0.0800"),
    ]

    summary = build_bucket_summary(allocations)

    assert [item["bucket"] for item in summary] == [
        "core",
        "jun_core",
        "satellite_core",
        "satellite",
        "pension",
        "liquidity",
        "other",
    ]
    assert summary[0]["market_value_jpy"] == Decimal("1800000")
    assert summary[4]["market_value_jpy"] == 0


def test_svg_pie_chart_matches_expected_format() -> None:
    summary = [
        {"bucket": "core", "market_value_jpy": Decimal("1800000"), "pct": Decimal("0.3600")},
        {"bucket": "jun_core", "market_value_jpy": Decimal("800000"), "pct": Decimal("0.1600")},
        {"bucket": "other", "market_value_jpy": 0, "pct": None},
    ]

    svg = build_portfolio_pie_svg(summary)

    assert "<svg" in svg
    assert "Portfolio Allocation" in svg
    assert 'fill="#2E86AB"' in svg
    assert 'fill="#F6C85F"' in svg
    assert "other" not in svg


def test_readme_embeds_rendered_image_markdown() -> None:
    markdown = build_readme_image_markdown()

    assert markdown == "![Portfolio Allocation](docs/portfolio_allocation_latest.svg)"


def test_bucket_summary_table_includes_snapshot_values() -> None:
    summary = [
        {"bucket": "core", "market_value_jpy": Decimal("1800000"), "pct": Decimal("0.3600")},
        {"bucket": "liquidity", "market_value_jpy": Decimal("1200000"), "pct": Decimal("0.2400")},
    ]

    table = build_bucket_summary_table(summary)

    assert "| bucket | market_value_jpy | pct |" in table
    assert "| core | 1800000 | 36.00% |" in table
    assert "| liquidity | 1200000 | 24.00% |" in table


def test_readme_marker_section_only_is_replaced() -> None:
    original = "\n".join(
        [
            "# Title",
            "before",
            "<!-- portfolio-piechart:start -->",
            "old",
            "<!-- portfolio-piechart:end -->",
            "after",
        ]
    )

    updated = update_readme_portfolio_section(
        original,
        snapshot_date="2026-03-29",
        total_assets_jpy=33028136,
        bucket_summary=[{"bucket": "core", "market_value_jpy": Decimal("1"), "pct": Decimal("0.0100")}],
    )

    assert "before" in updated
    assert "after" in updated
    assert "old" not in updated
    assert "snapshot_date: 2026-03-29" in updated
    assert "![Portfolio Allocation](docs/portfolio_allocation_latest.svg)" in updated


def test_readme_marker_is_inserted_when_missing() -> None:
    original = "# Title\n\nIntro\n\n## 目的\nbody"

    updated = update_readme_portfolio_section(
        original,
        snapshot_date="2026-03-29",
        total_assets_jpy=33028136,
        bucket_summary=[{"bucket": "core", "market_value_jpy": Decimal("1"), "pct": Decimal("0.0100")}],
    )

    assert "<!-- portfolio-piechart:start -->" in updated
    assert "## Latest Portfolio Snapshot" in updated
    assert updated.index("## Latest Portfolio Snapshot") < updated.index("## 目的")


def test_refresh_readme_portfolio_writes_snapshot_date_and_total_assets(tmp_path: Path) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# Title\n\n## 目的\nbody\n", encoding="utf-8")

    refresh_readme_portfolio(
        readme_path=readme_path,
        snapshot_date="2026-03-29",
        total_assets_jpy=33028136,
        bucket_allocations=[
            make_allocation("core", "5419420", "0.1641"),
            make_allocation("jun_core", "3086731", "0.0935"),
            make_allocation("satellite_core", "5143392", "0.1557"),
            make_allocation("satellite", "206392", "0.0062"),
            make_allocation("pension", "3381281", "0.1024"),
            make_allocation("liquidity", "14942636", "0.4524"),
            make_allocation("other", "848281", "0.0257"),
        ],
    )

    updated = readme_path.read_text(encoding="utf-8")
    assert "snapshot_date: 2026-03-29" in updated
    assert "total_assets_jpy: 33028136" in updated
    assert "![Portfolio Allocation](docs/portfolio_allocation_latest.svg)" in updated
    assert "| other | 848281 | 2.57% |" in updated
    svg = (tmp_path / "docs/portfolio_allocation_latest.svg").read_text(encoding="utf-8")
    assert "<svg" in svg
    assert "core (16.41%)" in svg
