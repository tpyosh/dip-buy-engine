from __future__ import annotations


from monthly_limit_order_review.thesis_metrics import build_long_term_thesis_targets


def test_only_enabled_held_symbols_are_included(
    sample_snapshot,
    portfolio_policy_config,
    sample_portfolio_analysis,
) -> None:
    targets = build_long_term_thesis_targets(
        sample_snapshot,
        portfolio_policy_config,
        sample_portfolio_analysis["resolved_buckets"],
        sample_portfolio_analysis["symbol_weights"],
    )

    assert [item["symbol"] for item in targets] == ["MSFT", "PLTR"]
    assert all(item["web_review_required"] == "yes" for item in targets)


def test_symbols_without_thesis_definition_are_excluded(
    sample_snapshot,
    portfolio_policy_config,
    sample_portfolio_analysis,
) -> None:
    targets = build_long_term_thesis_targets(
        sample_snapshot,
        portfolio_policy_config,
        sample_portfolio_analysis["resolved_buckets"],
        sample_portfolio_analysis["symbol_weights"],
    )

    symbols = {item["symbol"] for item in targets}
    assert "ALL_COUNTRY_FUND" not in symbols
    assert "NIKKO_SOX_FUND" not in symbols
    assert "JPY_CASH" not in symbols
