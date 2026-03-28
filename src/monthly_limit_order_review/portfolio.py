from __future__ import annotations

from .portfolio_metrics import compute_portfolio_metrics, format_pct, resolve_bucket


def analyze_portfolio(snapshot, policy_config):
    return compute_portfolio_metrics(snapshot, policy_config)

