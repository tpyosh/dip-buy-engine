from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Callable
from zoneinfo import ZoneInfo

from .market_data import MarketDataFetcher
from .models import Holding, MarketReference, MonthlyComputation, PortfolioSnapshot, PortfolioWarning
from .portfolio_metrics import suggest_core_proxy_symbol
from .review_readiness import build_account_type_gate, require_complete_account_type_gate
from .utils import quantize

ON_DEMAND_SCOPES = ("stocks", "investment_funds", "pension")


def assess_snapshot_freshness(
    snapshot_date: date,
    *,
    requested_at: datetime | None = None,
    max_age_days: int = 1,
    timezone: str = "Asia/Tokyo",
) -> dict[str, object]:
    if max_age_days < 0:
        raise ValueError("max_age_days must be zero or greater")
    current = requested_at or datetime.now(UTC)
    assessment_timezone = ZoneInfo(timezone)
    local_current = current.astimezone(assessment_timezone)
    age_days = (local_current.date() - snapshot_date).days
    if age_days < 0:
        status = "future_dated"
    elif age_days <= max_age_days:
        status = "fresh"
    else:
        status = "stale"
    return {
        "status": status,
        "snapshot_date": snapshot_date.isoformat(),
        "requested_at": current.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "requested_at_local": local_current.isoformat(timespec="seconds"),
        "timezone": timezone,
        "age_days": age_days,
        "max_age_days": max_age_days,
    }


def build_health_check_window(
    *,
    requested_at: datetime,
    base_lookback_days: int = 14,
    last_completed_at: datetime | None = None,
    overlap_days: int = 2,
    maximum_lookback_days: int = 90,
) -> dict[str, object]:
    """Return a gap-tolerant news window that does not assume daily execution."""

    if base_lookback_days < 1 or overlap_days < 0 or maximum_lookback_days < 1:
        raise ValueError("health-check lookback settings are invalid")
    requested_utc = requested_at.astimezone(UTC)
    if last_completed_at is None:
        required_days = max(base_lookback_days, 30)
        status = "initial_baseline"
    else:
        gap_days = max(0, (requested_utc.date() - last_completed_at.astimezone(UTC).date()).days)
        required_days = max(base_lookback_days, gap_days + overlap_days)
        status = "gap_recovery" if required_days > base_lookback_days else "normal"
    effective_days = min(required_days, maximum_lookback_days)
    if effective_days < required_days:
        status = "capped_gap_recovery"
    return {
        "status": status,
        "coverage_start": (requested_utc.date() - timedelta(days=effective_days)).isoformat(),
        "coverage_end": requested_utc.date().isoformat(),
        "effective_lookback_days": effective_days,
        "base_lookback_days": base_lookback_days,
        "maximum_lookback_days": maximum_lookback_days,
        "overlap_days": overlap_days,
        "last_completed_at": (
            last_completed_at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            if last_completed_at is not None
            else None
        ),
        "continuous_daily_execution_required": False,
        "comprehensive_review_is_decision_authority": True,
    }


def classify_on_demand_holdings(
    snapshot: PortfolioSnapshot,
    *,
    resolved_buckets: dict[str, str] | None = None,
) -> dict[str, list[Holding]]:
    resolved = resolved_buckets or {}
    groups: dict[str, list[Holding]] = {scope: [] for scope in ON_DEMAND_SCOPES}
    groups["context_only"] = []

    for holding in snapshot.holdings:
        bucket = resolved.get(holding.symbol, holding.asset_class)
        source_category = (holding.source_category or "").lower()
        account_type = (holding.account_type or "").lower()
        name = holding.name.lower()

        if (
            bucket == "pension"
            or "年金" in source_category
            or "年金" in account_type
            or "ideco" in account_type
        ):
            groups["pension"].append(holding)
        elif "投資信託" in source_category or _looks_like_investment_fund(holding, name=name, bucket=bucket):
            groups["investment_funds"].append(holding)
        elif "株式" in source_category or _looks_like_stock(holding, bucket=bucket):
            groups["stocks"].append(holding)
        else:
            groups["context_only"].append(holding)
    return groups


def _looks_like_investment_fund(holding: Holding, *, name: str, bucket: str) -> bool:
    fund_markers = ("投信", "ファンド", "fund", "index", "emaxis", "オールカントリー", "s&p500")
    return holding.quantity is None and bucket not in {"liquidity", "other"} and any(
        marker in name for marker in fund_markers
    )


def _looks_like_stock(holding: Holding, *, bucket: str) -> bool:
    return holding.quantity is not None and bucket not in {"liquidity", "pension", "other"}


def build_on_demand_reference_requests(
    snapshot: PortfolioSnapshot,
    tickers: dict,
    *,
    resolved_buckets: dict[str, str] | None = None,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    groups = classify_on_demand_holdings(snapshot, resolved_buckets=resolved_buckets)
    yfinance_symbols = tickers.get("yfinance_symbols", {})
    requests: dict[str, dict[str, str]] = {}
    missing_symbols: list[str] = []

    for scope in ON_DEMAND_SCOPES:
        for holding in groups[scope]:
            yfinance_symbol = yfinance_symbols.get(holding.symbol)
            if yfinance_symbol is None and scope in {"investment_funds", "pension"}:
                yfinance_symbol = suggest_core_proxy_symbol(holding)
            if yfinance_symbol is None:
                missing_symbols.append(holding.symbol)
                continue
            requests[holding.symbol] = {
                "yfinance_symbol": yfinance_symbol,
                "currency": _reference_currency(yfinance_symbol),
            }
    return requests, sorted(set(missing_symbols))


def _reference_currency(yfinance_symbol: str) -> str:
    if yfinance_symbol.endswith(".T") or yfinance_symbol.endswith("=X"):
        return "JPY"
    return "USD"


ReferenceFetcher = Callable[[str, str, str], MarketReference]


def enrich_on_demand_market_references(
    computation: MonthlyComputation,
    tickers: dict,
    *,
    reference_fetcher: ReferenceFetcher | None = None,
) -> dict[str, object]:
    requests, missing_symbols = build_on_demand_reference_requests(
        computation.snapshot,
        tickers,
        resolved_buckets=computation.metadata.get("resolved_buckets", {}),
    )
    existing_symbols = {reference.symbol for reference in computation.market_references}
    fetcher = reference_fetcher or MarketDataFetcher().fetch_reference
    failed: dict[str, str] = {}
    fetched_symbols: list[str] = []

    for symbol, params in requests.items():
        if symbol in existing_symbols:
            continue
        try:
            reference = fetcher(symbol, params["yfinance_symbol"], params["currency"])
        except Exception as exc:  # noqa: BLE001
            failed[symbol] = str(exc)
            continue
        computation.market_references.append(reference)
        existing_symbols.add(symbol)
        fetched_symbols.append(symbol)

    for symbol in missing_symbols:
        computation.warnings.append(
            PortfolioWarning(
                code="on_demand_market_reference_mapping_missing",
                severity="warning",
                message=f"No yfinance symbol or proxy is configured for on-demand holding {symbol}.",
                related_symbols=[symbol],
            )
        )
    for symbol, message in failed.items():
        computation.warnings.append(
            PortfolioWarning(
                code="on_demand_market_reference_fetch_failed",
                severity="warning",
                message=f"Could not fetch on-demand market reference for {symbol}: {message}",
                related_symbols=[symbol],
            )
        )

    return {
        "requested_symbols": sorted(requests),
        "already_available_symbols": sorted(set(requests) & (existing_symbols - set(fetched_symbols))),
        "fetched_symbols": sorted(fetched_symbols),
        "missing_mapping_symbols": missing_symbols,
        "failed_symbols": failed,
    }


def build_on_demand_market_data_artifact(computation: MonthlyComputation) -> dict[str, object]:
    groups = classify_on_demand_holdings(
        computation.snapshot,
        resolved_buckets=computation.metadata.get("resolved_buckets", {}),
    )
    reference_map = {reference.symbol: reference for reference in computation.market_references}
    on_demand_metadata = computation.metadata.get("on_demand", {})
    return {
        "kind": "on_demand_held_symbol_market_data",
        "generated_at": computation.generated_at,
        "account_type_gate": build_account_type_gate(computation.snapshot),
        "inventory": {
            "source_path": computation.metadata.get("snapshot_path"),
            "snapshot_date": computation.snapshot.snapshot_date,
            "freshness": on_demand_metadata.get("inventory_freshness", {}),
            "usage": "held_symbol_names_only",
        },
        "news_lookback_days": on_demand_metadata.get("news_lookback_days"),
        "health_check_window": on_demand_metadata.get("health_check_window", {}),
        "security_story_targets": list(computation.security_story_targets),
        "instruments": {
            scope: [
                {
                    "symbol": holding.symbol,
                    "name": holding.name,
                    "market_reference": reference_map.get(holding.symbol),
                }
                for holding in groups[scope]
            ]
            for scope in ON_DEMAND_SCOPES
        },
        "market_reference_collection": on_demand_metadata.get("market_reference_collection", {}),
        "warnings": [
            warning
            for warning in computation.warnings
            if warning.code.startswith("on_demand_")
        ],
    }


def render_on_demand_assessment_prompt(
    computation: MonthlyComputation,
    template_text: str,
    *,
    inventory_freshness: dict[str, object],
    news_lookback_days: int = 14,
    health_check_window: dict[str, object] | None = None,
) -> str:
    if news_lookback_days < 1:
        raise ValueError("news_lookback_days must be one or greater")
    snapshot = computation.snapshot
    account_type_gate = require_complete_account_type_gate(snapshot)
    resolved_buckets = computation.metadata.get("resolved_buckets", {})
    groups = classify_on_demand_holdings(snapshot, resolved_buckets=resolved_buckets)
    reference_map = {reference.symbol: reference for reference in computation.market_references}
    collection = computation.metadata.get("on_demand", {}).get("market_reference_collection", {})
    assessment_date = date.fromisoformat(str(inventory_freshness["requested_at_local"])[:10])
    window = health_check_window or {
        "status": "explicit",
        "coverage_start": (assessment_date - timedelta(days=news_lookback_days)).isoformat(),
        "coverage_end": assessment_date.isoformat(),
        "effective_lookback_days": news_lookback_days,
        "continuous_daily_execution_required": False,
        "comprehensive_review_is_decision_authority": True,
    }

    lines = [
        template_text.strip(),
        "",
        "## 1. アセスメント依頼時点とデータの役割",
        f"- requested_at: {inventory_freshness['requested_at']}",
        f"- requested_at_local: {inventory_freshness['requested_at_local']}",
        f"- timezone: {inventory_freshness['timezone']}",
        f"- holdings_inventory_snapshot_date: {inventory_freshness['snapshot_date']}",
        f"- holdings_inventory_age_days: {inventory_freshness['age_days']}",
        f"- holdings_inventory_status: {inventory_freshness['status']}",
        f"- account_type_gate_status: {account_type_gate['status']}",
        f"- account_type_gate_checked_holding_count: {account_type_gate['checked_holding_count']}",
        "- holdings_inventory_usage: 銘柄名の特定だけに使用し、保有額・数量・取得単価・損益・配分は評価しない",
        "- market_price_basis: yfinance latest available daily close; intraday real-time quote is not guaranteed",
        f"- authoritative_news_lookback_days: {news_lookback_days}",
        f"- health_check_window: {window}",
        f"- computation_generated_at: {computation.generated_at}",
        f"- holdings_inventory_source: {snapshot.source_evidence or {}}",
        "",
        "## 2. アセスメント対象",
        f"- stocks_count: {len(groups['stocks'])}",
        f"- investment_funds_count: {len(groups['investment_funds'])}",
        f"- pension_count: {len(groups['pension'])}",
        f"- ignored_non_investment_symbols: {[holding.symbol for holding in groups['context_only']]}",
        f"- security_story_target_count: {len(computation.security_story_targets)}",
    ]

    lines.extend(
        [
            "",
            "### 2-1. 個別株・ETFストーリー評価対象",
            "`machine_id` はCodex向けYAML専用です。ユーザ向け回答では `human_label` のみを使ってください。",
            "| machine_id (Codex YAML only) | human_label | instrument_type | thesis_recorded | thesis_status | thesis_summary | user_holding_reason | user_disposition | user_sell_condition | invalidation_conditions | required_assessment |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for target in computation.security_story_targets:
        lines.append(
            f"| {target['symbol']} | {_normalize_cell(target['name'])} | {target['instrument_type']} | "
            f"{str(target['thesis_recorded']).lower()} | {target['thesis_status']} | "
            f"{_normalize_cell(target.get('thesis_summary') or '')} | "
            f"{_normalize_cell(target.get('user_holding_reason') or '')} | "
            f"{_normalize_cell(target.get('user_disposition') or '')} | "
            f"{_normalize_cell(target.get('user_sell_condition') or '')} | "
            f"{_normalize_cell('; '.join(target.get('invalidation_conditions', [])))} | "
            f"{_normalize_cell(target['required_assessment'])} |"
        )

    section_names = {
        "stocks": "3. 株式",
        "investment_funds": "4. 投資信託",
        "pension": "5. 年金",
    }
    for scope in ON_DEMAND_SCOPES:
        lines.extend(["", f"## {section_names[scope]}"])
        lines.extend(
            _build_instrument_market_table(
                groups[scope],
                reference_map,
                assessment_date=assessment_date,
            )
        )

    lines.extend(
        [
            "",
            "## 6. 価格取得状況・警告・不確実性",
            f"- market_reference_collection: {collection}",
        ]
    )
    market_warnings = [
        warning for warning in computation.warnings if warning.code.startswith("on_demand_")
    ]
    if market_warnings:
        for warning in market_warnings:
            related = f" related={','.join(warning.related_symbols)}" if warning.related_symbols else ""
            lines.append(f"- [{warning.severity}] {warning.code}: {warning.message}{related}")
    else:
        lines.append("- なし")
    if snapshot.ocr_notes:
        lines.append("- holdings_inventory_note: 元スナップショットにはOCR注記がありますが、保有銘柄名以外は評価に使わないでください")
    lines.extend(
        [
            "",
            "## 7. 提出物契約",
            "- ユーザ向け: 日本語Markdownで、重要な変化、緊急度、判断が必要な事項を簡潔に提示する。正式な商品名・会社名を使い、銘柄コード・ティッカー・内部IDを表示しない。",
            "- Codex向け: `health_check_response.yaml` を別ファイルで提出する。YAML内にMarkdownや前置きを混ぜない。",
            "- 機械IDはCodex向けYAMLの `symbol` フィールドにだけ残し、human_summaryなど人間向け文字列へ混ぜない。",
            "- YAMLでは security_story_targets の全銘柄を一件ずつ記録し、evaluated、story_health、decision、decision_rationale、next_review_triggers、sourcesを必須とする。",
            "- decisionは add / hold / reduce / exit / no_add_pending_thesis、story_healthは healthy / watch / impaired / broken / insufficient_evidence のいずれかにする。",
            "- 投資待機資金は維持自体を目的にしない。市場下落時は dip_buy_liquidity_deployment_review.use_option に対象、金額または算式、時期、根拠を持つ使用案を必ず記録する。",
            "- 最終選択が hold でも使用案の比較は省略せず、reserve_maintenance_is_objective は false とする。",
            "- 毎日の連続実行は前提にしない。調査期間に空白がある場合は health_check_window 全体を確認する。",
            "- schema_ref: schemas/health-check-response.schema.yaml",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _build_instrument_market_table(
    holdings: list[Holding],
    reference_map: dict[str, MarketReference],
    *,
    assessment_date: date,
) -> list[str]:
    lines = [
        "| symbol | name | reference_symbol | reference_role | current_price | return_1d_pct | return_5d_pct | return_1m_pct | return_3m_pct | drawdown_21d_pct | drawdown_63d_pct | currency | market_as_of | market_age_days |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    if not holdings:
        lines.append("| - | - | - | - | - | - | - | - | - | - | - | - | - | - |")
        return lines
    for holding in holdings:
        reference = reference_map.get(holding.symbol)
        if reference is None:
            lines.append(
                f"| {holding.symbol} | {_normalize_cell(holding.name)} | - | missing | - | - | - | - | - | - | - | - | - | - |"
            )
            continue
        lines.append(
            f"| {holding.symbol} | {_normalize_cell(holding.name)} | "
            f"{reference.yfinance_symbol} | {_reference_role(reference)} | {_value(reference.current_price)} | "
            f"{_value(_percent_change(reference.current_price, reference.prior_close_1d))} | "
            f"{_value(_percent_change(reference.current_price, reference.prior_close_5d))} | "
            f"{_value(_percent_change(reference.current_price, reference.prior_close_21d))} | "
            f"{_value(_percent_change(reference.current_price, reference.prior_close_63d))} | "
            f"{_value(_drawdown(reference.current_price, reference.recent_high_21d))} | "
            f"{_value(_drawdown(reference.current_price, reference.recent_high_63d))} | "
            f"{reference.currency} | {reference.as_of} | {(assessment_date - reference.as_of).days} |"
        )
    return lines


def _reference_role(reference: MarketReference) -> str:
    direct_symbols = {reference.symbol, f"{reference.symbol}.T"}
    return "direct" if reference.yfinance_symbol in direct_symbols else "proxy"


def _percent_change(current: Decimal | None, prior: Decimal | None) -> Decimal | None:
    if current in (None, 0) or prior in (None, 0):
        return None
    return quantize((current - prior) / prior * 100, 2)


def _drawdown(current: Decimal | None, high: Decimal | None) -> Decimal | None:
    if current in (None, 0) or high in (None, 0):
        return None
    return quantize((current - high) / high * 100, 2)


def _value(value: object) -> str:
    return "null" if value is None else str(value)


def _normalize_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
