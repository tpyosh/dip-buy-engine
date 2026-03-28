from __future__ import annotations

from decimal import Decimal


def test_exposure_breakdown_total_matches_included_rows(sample_exposure_breakdown) -> None:
    included_total = sum(
        (
            item["value_jpy"]
            for item in sample_exposure_breakdown["breakdown"]
            if item["included_in_semiconductor_exposure"] == "yes"
        ),
        start=Decimal("0"),
    )

    assert included_total == sample_exposure_breakdown["semiconductor_exposure_total_jpy"]
    assert sample_exposure_breakdown["semiconductor_exposure_total_pct"] == Decimal("0.1600")


def test_optional_symbols_can_be_listed_but_excluded(sample_exposure_breakdown) -> None:
    msft = next(item for item in sample_exposure_breakdown["breakdown"] if item["symbol"] == "MSFT")

    assert msft["included_in_semiconductor_exposure"] == "no"
    assert msft["inclusion_reason"] == "config_optional_excluded"

