from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class Holding:
    symbol: str
    name: str
    asset_class: str
    quantity: Decimal | None
    avg_cost: Decimal | None
    current_price: Decimal | None
    market_value_jpy: Decimal
    currency: str


@dataclass(slots=True)
class PortfolioSnapshot:
    snapshot_date: date
    currency_base: str
    total_assets_jpy: Decimal
    liquidity_target_jpy: Decimal | None
    holdings: list[Holding]
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BucketAllocation:
    bucket: str
    market_value_jpy: Decimal
    actual_pct: Decimal
    target_pct: Decimal | None
    delta_pct: Decimal | None
    preferred_min_pct: Decimal | None
    preferred_max_pct: Decimal | None


@dataclass(slots=True)
class MarketReference:
    symbol: str
    yfinance_symbol: str
    current_price: Decimal | None
    mean_close_20d: Decimal | None
    recent_high_21d: Decimal | None
    recent_high_63d: Decimal | None
    currency: str
    as_of: date


@dataclass(slots=True)
class TrancheRule:
    drawdown_pct: Decimal
    shares: int


@dataclass(slots=True)
class CandidateOrder:
    symbol: str
    bucket: str
    base_price: Decimal | None
    current_price: Decimal | None
    limit_price: Decimal | None
    shares: int
    estimated_cost: Decimal | None
    estimated_cost_jpy: Decimal | None
    currency: str
    drawdown_pct: Decimal | None
    drawdown_rule: str
    reference_method: str
    suppressed: bool = False
    suppressed_reason_code: str | None = None
    suppressed_reason_text: str | None = None
    note_for_chatgpt: str | None = None
    suppression_reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PortfolioWarning:
    code: str
    message: str
    severity: str = "warning"
    related_symbols: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MonthlyComputation:
    snapshot: PortfolioSnapshot
    generated_at: str
    bucket_allocations: list[BucketAllocation]
    market_references: list[MarketReference]
    candidate_orders: list[CandidateOrder]
    warnings: list[PortfolioWarning]
    semi_exposure_pct: Decimal
    liquidity_jpy: Decimal
    sox_buy_signal: dict
    portfolio_summary: dict = field(default_factory=dict)
    core_buy_materials: dict = field(default_factory=dict)
    exposure_breakdown: dict = field(default_factory=dict)
    long_term_thesis_targets: list[dict] = field(default_factory=list)
    monthly_execution_outputs: dict = field(default_factory=dict)
    quarterly_rule_review_outputs: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class PromptArtifact:
    kind: str
    snapshot_month: str
    content: str
    output_path: str


@dataclass(slots=True)
class ReviewOrderProposal:
    symbol: str
    recommended_price: Decimal | None
    recommended_shares: int | None
    reason: str


@dataclass(slots=True)
class ReviewFeedback:
    raw_text: str
    sections: dict[str, str]
    order_proposals: list[ReviewOrderProposal]
    sox_decision: str | None
    portfolio_diagnosis: list[str]
    rule_review: list[str]
    must: list[str]
    should: list[str]
    nice_to_have: list[str]
    parser_warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProposalDiff:
    symbol: str
    python_price: Decimal | None
    chatgpt_price: Decimal | None
    price_diff_pct: Decimal | None
    python_shares: int | None
    chatgpt_shares: int | None
    reason_summary: str
    added_warnings: list[str] = field(default_factory=list)
    candidate_removed: bool = False


@dataclass(slots=True)
class CodexPatchRequest:
    snapshot_month: str
    must: list[str]
    should: list[str]
    nice_to_have: list[str]
    objectives: list[str]
    target_files: list[str]
    spec_diffs: list[str]
    tests_to_update: list[str]
    backward_compatibility_notes: list[str]
