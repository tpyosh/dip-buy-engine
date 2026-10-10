from __future__ import annotations

import argparse
import json
import logging
import sys
from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from .calendar_events import build_core_spot_buy_calendar_event_drafts, load_core_spot_buy_event_config
from .candidate_metrics import compute_candidate_metrics
from .codex_patch_builder import build_codex_patch_prompt, build_codex_patch_request
from .context_records import (
    apply_holding_metadata,
    holding_metadata_by_symbol,
    load_financial_context,
    load_holding_metadata_context,
)
from .current_state import build_current_state_projection
from .diff_analyzer import build_proposal_diffs
from .exposure_metrics import build_exposure_breakdown
from .independent_decision import (
    load_independent_decision_response,
    render_independent_decision_prompt,
    validate_independent_decision_request,
)
from .market_data import fetch_intraday_quote, fetch_market_references
from .models import MonthlyComputation, PortfolioSnapshot, PortfolioWarning
from .on_demand import (
    assess_snapshot_freshness,
    build_health_check_window,
    build_on_demand_market_data_artifact,
    enrich_on_demand_market_references,
    render_on_demand_assessment_prompt,
)
from .portfolio_metrics import build_core_buy_materials, compute_portfolio_metrics, suggest_core_proxy_symbol
from .prompt_renderer import render_chatgpt_prompt, render_review_generation_blocker
from .review_packet import build_review_packet
from .review_readiness import build_account_type_gate, require_complete_account_type_gate
from .repository_records import (
    audit_repository,
    load_recurring_contribution_context,
    load_thesis_monitoring_policy,
    raise_for_repository_errors,
)
from .review_parser import parse_review_feedback
from .rules import calculate_sox_buy_signal
from .snapshot_loader import load_snapshot
from .storage import default_output_paths, load_yaml, on_demand_output_paths, read_text, write_text, write_yaml
from .story_health import build_security_story_targets
from .strategy_policy import load_current_strategy_context
from .structured_review import load_health_check_response, load_monthly_review_response
from .thesis_metrics import build_long_term_thesis_targets
from .utils import infer_target_month_start, month_key, percent, quantize, target_month_key
from .validation import (
    apply_candidate_validations,
    build_exposure_validation_warnings,
    build_snapshot_validation_warnings,
    build_validation_warnings,
)

LOGGER = logging.getLogger(__name__)
LEGACY_ASSUMED_MONTHLY_CASH_INFLOW_JPY = Decimal("650000")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)

    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001
        LOGGER.error(str(exc))
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="On-demand investment review CLI")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    review_parser = subparsers.add_parser("generate-review-prompt", help="Generate an on-demand ChatGPT comprehensive review prompt")
    review_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    review_parser.add_argument("--output", required=False, help="Path to output markdown prompt")
    review_parser.set_defaults(func=handle_generate_review_prompt)

    ingest_parser = subparsers.add_parser("ingest-review", help="Ingest a ChatGPT review text file")
    ingest_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    ingest_source = ingest_parser.add_mutually_exclusive_group(required=True)
    ingest_source.add_argument("--review-yaml", help="Path to ChatGPT review_response.yaml (preferred)")
    ingest_source.add_argument("--review-text", help="Path to legacy saved ChatGPT review text")
    ingest_parser.set_defaults(func=handle_ingest_review)

    codex_parser = subparsers.add_parser("generate-codex-patch", help="Generate a Codex patch prompt")
    codex_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    codex_source = codex_parser.add_mutually_exclusive_group(required=True)
    codex_source.add_argument("--review-yaml", help="Path to ChatGPT review_response.yaml (preferred)")
    codex_source.add_argument("--review-text", help="Path to legacy saved ChatGPT review text")
    codex_parser.add_argument("--output", required=False, help="Path to output markdown prompt")
    codex_parser.set_defaults(func=handle_generate_codex_patch)

    monthly_parser = subparsers.add_parser("monthly-run", help="Compatibility command: generate an on-demand comprehensive review from a dated snapshot")
    monthly_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    monthly_parser.set_defaults(func=handle_monthly_run)

    decision_parser = subparsers.add_parser(
        "on-demand-decision-prompt",
        help="Generate a self-contained independent ChatGPT decision prompt",
    )
    decision_parser.add_argument(
        "--request",
        required=True,
        help="Path to an independent decision request YAML",
    )
    decision_parser.add_argument(
        "--output",
        required=True,
        help="Path for the generated Markdown prompt",
    )
    decision_parser.set_defaults(func=handle_on_demand_decision_prompt)

    decision_validate_parser = subparsers.add_parser(
        "validate-independent-decision",
        help="Validate an independent ChatGPT decision response against its request",
    )
    decision_validate_parser.add_argument(
        "--request",
        required=True,
        help="Path to the original independent decision request YAML",
    )
    decision_validate_parser.add_argument(
        "--response-yaml",
        required=True,
        help="Path to ChatGPT independent_decision_response.yaml",
    )
    decision_validate_parser.set_defaults(func=handle_validate_independent_decision)

    for command, help_text in (
        (
            "health-check-run",
            "Run a gap-tolerant held-security story, market, and news health check",
        ),
        (
            "on-demand-run",
            "Compatibility alias for health-check-run",
        ),
    ):
        on_demand_parser = subparsers.add_parser(command, help=help_text)
        on_demand_parser.add_argument(
            "--snapshot",
            required=False,
            help="Path to a snapshot used only as a held-symbol inventory (latest normalized snapshot by default)",
        )
        on_demand_parser.add_argument("--output", required=False, help="Path to output markdown prompt")
        on_demand_parser.add_argument(
            "--inventory-max-age-days",
            type=int,
            default=45,
            help="Age after which the held-symbol inventory is labeled stale (default: 45; never blocks price fetch)",
        )
        on_demand_parser.add_argument(
            "--news-lookback-days",
            type=int,
            default=14,
            help="Minimum authoritative-news lookback; gaps expand this automatically (default: 14)",
        )
        on_demand_parser.add_argument(
            "--max-news-lookback-days",
            type=int,
            default=90,
            help="Maximum automatic gap-recovery lookback (default: 90)",
        )
        on_demand_parser.set_defaults(func=handle_on_demand_run)

    health_ingest_parser = subparsers.add_parser(
        "ingest-health-check",
        help="Validate and store a ChatGPT health_check_response.yaml",
    )
    health_ingest_parser.add_argument(
        "--response-yaml",
        required=True,
        help="Path to ChatGPT health_check_response.yaml",
    )
    health_ingest_parser.add_argument(
        "--request-dir",
        required=False,
        help="Generated health-check request directory (latest by default)",
    )
    health_ingest_parser.set_defaults(func=handle_ingest_health_check)

    audit_parser = subparsers.add_parser(
        "repository-audit",
        help="Validate repository sources of truth and cross-file references without writing files",
    )
    audit_parser.set_defaults(func=handle_repository_audit)

    quote_parser = subparsers.add_parser(
        "intraday-quote",
        help="Fetch the latest available one-minute close with timestamp and freshness metadata",
    )
    quote_parser.add_argument("--symbol", required=True, help="Repository symbol")
    quote_parser.add_argument("--yfinance-symbol", required=False, help="Provider symbol; defaults to --symbol")
    quote_parser.add_argument("--currency", default="USD", help="Quote currency (default: USD)")
    quote_parser.set_defaults(func=handle_intraday_quote)
    return parser


def configure_logging(*, verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def handle_repository_audit(args: argparse.Namespace) -> int:
    del args
    project_root = get_project_root()
    issues = audit_repository(project_root)
    for issue in issues:
        log = LOGGER.warning if issue["severity"] == "warning" else LOGGER.error
        log("%s: %s", issue["code"], issue["message"])
    raise_for_repository_errors(issues)
    warning_count = sum(issue["severity"] == "warning" for issue in issues)
    LOGGER.info("Repository audit passed with %s warning(s).", warning_count)
    return 0


def handle_intraday_quote(args: argparse.Namespace) -> int:
    quote = fetch_intraday_quote(
        args.symbol,
        yfinance_symbol=args.yfinance_symbol,
        currency=args.currency,
    )
    print(json.dumps(quote, ensure_ascii=False, indent=2))
    return 0


def handle_generate_review_prompt(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    snapshot_path = Path(args.snapshot)
    computation = compute_monthly(
        snapshot_path,
        project_root=project_root,
        project_current_state=True,
    )
    paths = default_output_paths(project_root, target_month_key(computation.snapshot.snapshot_date, snapshot_path=snapshot_path))
    output_path = Path(args.output) if args.output else paths["review_prompt"]
    template_text = read_text(project_root / "prompts/templates/monthly_review_template.md")
    review_packet = build_current_review_packet(computation, project_root)
    write_yaml(paths["computation"], computation)
    write_yaml(paths["review_packet"], review_packet)
    if review_packet.generation_status != "ready":
        blocker = render_review_generation_blocker(review_packet)
        write_text(output_path, blocker)
        write_text(paths["review_prompt_history"], blocker)
        LOGGER.error(
            "Review prompt generation blocked: %s",
            review_packet.generation_status,
        )
        return 2
    prompt = render_chatgpt_prompt(
        computation,
        template_text,
        review_packet=review_packet,
    )
    write_text(output_path, prompt)
    write_text(paths["review_prompt_history"], prompt)
    LOGGER.info("Saved computation to %s", paths["computation"])
    LOGGER.info("Saved closed review packet to %s", paths["review_packet"])
    LOGGER.info("Saved review prompt to %s", output_path)
    return 0


def handle_ingest_review(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    snapshot_path = Path(args.snapshot)
    computation = compute_monthly(
        snapshot_path,
        project_root=project_root,
        project_current_state=True,
    )
    month = target_month_key(computation.snapshot.snapshot_date, snapshot_path=snapshot_path)
    response_payload, review_feedback, source_review_path = load_review_input(
        args,
        computation=computation,
        review_target_month=month,
    )
    diffs = build_proposal_diffs(computation.candidate_orders, review_feedback, computation.warnings)
    paths = default_output_paths(project_root, month)
    calendar_event_artifact = build_core_spot_buy_calendar_event_artifact(
        review_feedback=review_feedback,
        review_target_month=month,
        source_review_path=source_review_path,
        project_root=project_root,
    )

    write_yaml(paths["computation"], computation)
    write_yaml(paths["review_structured"], response_payload or review_feedback)
    write_yaml(paths["diff"], diffs)
    write_yaml(paths["calendar_events"], calendar_event_artifact)
    LOGGER.info("Saved structured review to %s", paths["review_structured"])
    LOGGER.info("Saved proposal diffs to %s", paths["diff"])
    LOGGER.info("Saved Google Calendar event drafts to %s", paths["calendar_events"])
    return 0


def handle_generate_codex_patch(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    snapshot_path = Path(args.snapshot)
    computation = compute_monthly(
        snapshot_path,
        project_root=project_root,
        project_current_state=True,
    )
    month = target_month_key(computation.snapshot.snapshot_date, snapshot_path=snapshot_path)
    response_payload, review_feedback, source_review_path = load_review_input(
        args,
        computation=computation,
        review_target_month=month,
    )
    diffs = build_proposal_diffs(computation.candidate_orders, review_feedback, computation.warnings)
    patch_request = build_codex_patch_request(month, review_feedback, diffs)
    paths = default_output_paths(project_root, month)
    output_path = Path(args.output) if args.output else paths["patch_prompt"]
    template_text = read_text(project_root / "prompts/templates/codex_patch_template.md")
    prompt = build_codex_patch_prompt(template_text, patch_request, diffs)
    calendar_event_artifact = build_core_spot_buy_calendar_event_artifact(
        review_feedback=review_feedback,
        review_target_month=month,
        source_review_path=source_review_path,
        project_root=project_root,
    )

    write_yaml(paths["computation"], computation)
    write_yaml(paths["review_structured"], response_payload or review_feedback)
    write_yaml(paths["diff"], diffs)
    write_yaml(paths["patch_request"], patch_request)
    write_yaml(paths["calendar_events"], calendar_event_artifact)
    write_text(output_path, prompt)
    LOGGER.info("Saved Codex patch request to %s", paths["patch_request"])
    LOGGER.info("Saved Google Calendar event drafts to %s", paths["calendar_events"])
    LOGGER.info("Saved Codex patch prompt to %s", output_path)
    return 0


def handle_on_demand_decision_prompt(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    request_path = Path(args.request)
    output_path = Path(args.output)
    request = load_yaml(request_path)
    template = read_text(
        project_root
        / "prompts/templates/on_demand_independent_decision_template.md"
    )
    prompt = render_independent_decision_prompt(request, template)
    write_text(output_path, prompt)
    LOGGER.info("Saved on-demand independent decision prompt to %s", output_path)
    return 0


def handle_validate_independent_decision(args: argparse.Namespace) -> int:
    request = load_yaml(Path(args.request))
    validate_independent_decision_request(request)
    decision_id = request.get("decision_id")
    if not decision_id:
        raise ValueError("Independent decision request is missing decision_id")
    load_independent_decision_response(
        args.response_yaml,
        expected_decision_id=str(decision_id),
        expected_holding_accounts={
            str(item["symbol"]): str(item["account_type"])
            for item in request["account_type_gate"]["confirmed_holdings"]
        },
    )
    LOGGER.info(
        "Independent decision response passed contract validation for %s",
        decision_id,
    )
    return 0


def load_review_input(
    args: argparse.Namespace,
    *,
    computation: MonthlyComputation,
    review_target_month: str,
) -> tuple[dict | None, object, Path]:
    project_root = get_project_root()
    review_packet = build_current_review_packet(computation, project_root)
    if review_packet.generation_status != "ready":
        raise ValueError(
            "Review response ingestion blocked because the current request is not review-ready: "
            + review_packet.generation_status
        )
    review_yaml = getattr(args, "review_yaml", None)
    if review_yaml:
        source_path = Path(review_yaml)
        payload, feedback = load_monthly_review_response(
            source_path,
            expected_month=review_target_month,
            expected_security_symbols={
                target["symbol"] for target in computation.security_story_targets
            },
            expected_thematic_member_symbols={
                symbol
                for target in review_packet.allowed_quantitative_facts[
                    "thematic_fund_review_targets"
                ]
                for symbol in target.get("member_symbols", [])
            },
            expected_cash_context=review_packet.allowed_quantitative_facts[
                "cash_requirement_inputs"
            ],
            expected_date_context={
                "portfolio_snapshot_as_of": review_packet.portfolio_snapshot_as_of,
                "market_reference_as_of": review_packet.market_reference_as_of,
                "packet_generated_at": review_packet.packet_generated_at,
                "research_cutoff_at": review_packet.research_cutoff_at,
            },
            total_assets_jpy=computation.snapshot.total_assets_jpy,
            expected_current_holding_symbols={
                str(holding["symbol"])
                for holding in review_packet.allowed_quantitative_facts["holdings"]
                if holding.get("asset_class")
                in {"core", "jun_core", "satellite_core", "satellite"}
            },
            expected_current_holding_accounts={
                str(holding["symbol"]): str(holding["account_type"])
                for holding in review_packet.allowed_quantitative_facts["holdings"]
                if holding.get("asset_class")
                in {"core", "jun_core", "satellite_core", "satellite"}
            },
        )
        return payload, feedback, source_path
    review_text_path = getattr(args, "review_text", None)
    if not review_text_path:
        raise ValueError("Either --review-yaml or --review-text is required")
    source_path = Path(review_text_path)
    return (
        None,
        parse_review_feedback(
            read_text(source_path),
            review_target_month=review_target_month,
        ),
        source_path,
    )


def handle_monthly_run(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    snapshot_path = Path(args.snapshot)
    computation = compute_monthly(
        snapshot_path,
        project_root=project_root,
        project_current_state=True,
    )
    paths = default_output_paths(project_root, target_month_key(computation.snapshot.snapshot_date, snapshot_path=snapshot_path))
    template_text = read_text(project_root / "prompts/templates/monthly_review_template.md")
    review_packet = build_current_review_packet(computation, project_root)
    write_yaml(paths["computation"], computation)
    write_yaml(paths["review_packet"], review_packet)
    if review_packet.generation_status != "ready":
        blocker = render_review_generation_blocker(review_packet)
        write_text(paths["review_prompt"], blocker)
        write_text(paths["review_prompt_history"], blocker)
        LOGGER.error(
            "On-demand review prompt generation blocked: %s",
            review_packet.generation_status,
        )
        return 2
    prompt = render_chatgpt_prompt(
        computation,
        template_text,
        review_packet=review_packet,
    )
    write_text(paths["review_prompt"], prompt)
    write_text(paths["review_prompt_history"], prompt)
    LOGGER.info("Saved computation to %s", paths["computation"])
    LOGGER.info("Saved closed review packet to %s", paths["review_packet"])
    LOGGER.info("Saved review prompt to %s", paths["review_prompt"])
    return 0


def build_current_review_packet(
    computation: MonthlyComputation,
    project_root: Path,
):
    financial_context = load_financial_context(project_root)
    return build_review_packet(
        computation,
        financial_context=financial_context["record"],
        financial_context_source=financial_context["source_path"],
    )


def handle_on_demand_run(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    snapshot_path = resolve_on_demand_inventory_path(project_root, args.snapshot)
    requested_at = datetime.now(UTC)
    last_completed_at = find_latest_completed_health_check(project_root)
    health_check_window = build_health_check_window(
        requested_at=requested_at,
        base_lookback_days=args.news_lookback_days,
        last_completed_at=last_completed_at,
        maximum_lookback_days=getattr(args, "max_news_lookback_days", 90),
    )
    snapshot = load_snapshot(snapshot_path)
    inventory_freshness = assess_snapshot_freshness(
        snapshot.snapshot_date,
        requested_at=requested_at,
        max_age_days=args.inventory_max_age_days,
    )
    if inventory_freshness["status"] == "future_dated":
        raise ValueError("Held-symbol inventory snapshot_date is in the future; verify the source file.")

    computation = compute_on_demand(
        snapshot_path,
        project_root=project_root,
        requested_at=requested_at,
    )
    require_complete_account_type_gate(computation.snapshot)
    tickers = load_yaml(project_root / "config/tickers.yaml")
    market_reference_path = project_root / "config/market_reference.yaml"
    if market_reference_path.exists():
        tickers.setdefault("yfinance_symbols", {}).update(
            load_yaml(market_reference_path).get("yfinance_symbols", {})
        )
    collection = enrich_on_demand_market_references(computation, tickers)
    computation.metadata["on_demand"] = {
        "inventory_freshness": inventory_freshness,
        "market_reference_collection": collection,
        "news_lookback_days": health_check_window["effective_lookback_days"],
        "health_check_window": health_check_window,
        "monthly_side_effects_disabled": True,
    }

    paths = on_demand_output_paths(project_root, requested_at)
    output_path = Path(args.output) if args.output else paths["prompt"]
    template_text = read_text(project_root / "prompts/templates/on_demand_assessment_template.md")
    prompt = render_on_demand_assessment_prompt(
        computation,
        template_text,
        inventory_freshness=inventory_freshness,
        news_lookback_days=int(health_check_window["effective_lookback_days"]),
        health_check_window=health_check_window,
    )

    market_data_artifact = build_on_demand_market_data_artifact(computation)
    write_yaml(paths["market_data"], market_data_artifact)
    write_text(output_path, prompt)
    write_text(paths["prompt_history"], prompt)
    LOGGER.info("Saved on-demand market data to %s", paths["market_data"])
    LOGGER.info("Saved on-demand assessment prompt to %s", output_path)
    LOGGER.info("Saved on-demand prompt history to %s", paths["prompt_history"])
    return 0


def find_latest_completed_health_check(project_root: Path) -> datetime | None:
    completed: list[datetime] = []
    output_root = project_root / "reports/generated/on_demand"
    for path in output_root.glob("**/health_check_response.yaml"):
        try:
            payload = load_yaml(path)
            raw_value = payload.get("completed_at") or payload.get("generated_at")
            if raw_value:
                parsed = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
                completed.append(parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC))
        except Exception:  # noqa: BLE001
            continue
    return max(completed) if completed else None


def handle_ingest_health_check(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    request_dir = (
        Path(args.request_dir)
        if args.request_dir
        else resolve_latest_health_check_request_dir(project_root)
    )
    market_data_path = request_dir / "market_data.yaml"
    if not market_data_path.exists():
        raise ValueError(f"Health-check market_data.yaml is missing: {market_data_path}")
    market_data = load_yaml(market_data_path)
    account_gate = market_data.get("account_type_gate")
    if not isinstance(account_gate, dict) or account_gate.get("status") != "complete":
        raise ValueError(
            "Health-check response ingestion blocked because the request did not pass the account type gate."
        )
    expected_symbols = {
        str(target["symbol"])
        for target in market_data.get("security_story_targets", [])
    }
    if not expected_symbols:
        raise ValueError("Health-check request has no security_story_targets")
    payload = load_health_check_response(
        args.response_yaml,
        expected_security_symbols=expected_symbols,
    )
    destination = request_dir / "health_check_response.yaml"
    write_yaml(destination, payload)
    LOGGER.info("Saved validated health-check response to %s", destination)
    return 0


def resolve_latest_health_check_request_dir(project_root: Path) -> Path:
    requests = list(
        (project_root / "reports/generated/on_demand").glob(
            "**/health_check_request.md"
        )
    )
    if not requests:
        raise ValueError("No generated health-check request is available")
    return max(requests, key=lambda path: path.parent.name).parent


def resolve_on_demand_inventory_path(project_root: Path, snapshot_arg: str | None) -> Path:
    if snapshot_arg:
        return Path(snapshot_arg)

    candidates: list[tuple[date, int, Path]] = []
    for path in (project_root / "data/normalized").glob("snapshot_*.yaml"):
        try:
            snapshot = load_snapshot(path)
        except Exception:  # noqa: BLE001
            continue
        candidates.append((snapshot.snapshot_date, path.stat().st_mtime_ns, path))
    if not candidates:
        raise ValueError("No readable normalized snapshot is available as a held-symbol inventory.")
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def compute_on_demand(
    snapshot_path: Path,
    *,
    project_root: Path,
    requested_at: datetime,
) -> MonthlyComputation:
    snapshot = load_snapshot(snapshot_path)
    holding_context = load_holding_metadata_context(project_root)
    apply_holding_metadata(snapshot, holding_context["record"])
    transaction_ledger = load_yaml(project_root / "transactions/ledger.yaml")
    snapshot, current_state_projection = build_current_state_projection(
        snapshot,
        holding_context["record"],
        transaction_ledger,
    )
    holding_metadata = holding_metadata_by_symbol(holding_context)
    resolved_buckets = {holding.symbol: holding.asset_class for holding in snapshot.holdings}
    thesis_policy = load_thesis_monitoring_policy(project_root)

    return MonthlyComputation(
        snapshot=snapshot,
        generated_at=requested_at.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        bucket_allocations=[],
        market_references=[],
        candidate_orders=[],
        warnings=[],
        semi_exposure_pct=Decimal("0"),
        liquidity_jpy=Decimal("0"),
        sox_buy_signal={},
        security_story_targets=build_security_story_targets(
            snapshot,
            thesis_policy,
            holding_metadata,
        ),
        metadata={
            "snapshot_path": str(snapshot_path),
            "holding_metadata_source": holding_context["source_path"],
            "holding_metadata_effective_from": holding_context["record"].get(
                "effective_from"
            ),
            "holding_execution_context": holding_context["record"].get(
                "execution_context", {}
            ),
            "current_state_projection": current_state_projection,
            "inventory_only": True,
            "resolved_buckets": resolved_buckets,
            "account_type_gate": build_account_type_gate(snapshot),
        },
    )


def build_core_spot_buy_calendar_event_artifact(
    *,
    review_feedback,
    review_target_month: str,
    source_review_path: Path,
    project_root: Path,
) -> dict:
    event_config = load_core_spot_buy_event_config(project_root)
    event_drafts = build_core_spot_buy_calendar_event_drafts(
        review_feedback,
        review_target_month=review_target_month,
        source_review_path=source_review_path,
        config=event_config,
    )
    return {
        "review_target_month": review_target_month,
        "source_review_text": str(source_review_path),
        "event_count": len(event_drafts),
        "events": event_drafts,
    }


def compute_monthly(
    snapshot_path: Path,
    *,
    project_root: Path,
    project_current_state: bool = False,
) -> MonthlyComputation:
    snapshot = load_snapshot(snapshot_path)
    holding_context = load_holding_metadata_context(project_root)
    apply_holding_metadata(snapshot, holding_context["record"])
    current_state_projection = None
    if project_current_state:
        snapshot, current_state_projection = build_current_state_projection(
            snapshot,
            holding_context["record"],
            load_yaml(project_root / "transactions/ledger.yaml"),
        )
    holding_metadata = holding_metadata_by_symbol(holding_context)
    review_target_month_start = infer_target_month_start(snapshot.snapshot_date, snapshot_path=snapshot_path)
    review_target_month = month_key(review_target_month_start)
    previous_snapshot, previous_snapshot_warnings = load_previous_snapshot_for_validation(
        snapshot_path,
        review_target_month_start,
    )
    buy_rules = load_yaml(project_root / "config/buy_rules.yaml")
    portfolio_policy = load_yaml(project_root / "config/portfolio_policy.yaml")
    tickers = load_yaml(project_root / "config/tickers.yaml")
    allocation_rules_path = project_root / "config/allocation_rules.yaml"
    market_reference_path = project_root / "config/market_reference.yaml"
    classification_overrides_path = project_root / "config/classification_overrides.yaml"
    strategy_context = load_applicable_strategy_context(
        project_root,
        review_target_month_start,
    )
    active_strategy = strategy_context.get("strategy")
    active_plans = strategy_context.get("active_plans", [])

    merged_buy_rules = deepcopy(buy_rules)
    if active_strategy is not None:
        merged_buy_rules.pop("core_budget_policy", None)
    elif allocation_rules_path.exists():
        allocation_rules = load_yaml(allocation_rules_path)
        if "core_budget_policy" in allocation_rules:
            merged_buy_rules["core_budget_policy"] = allocation_rules["core_budget_policy"]
    budget_policy_warnings: list[PortfolioWarning] = []
    if "core_budget_policy" in merged_buy_rules:
        merged_buy_rules["core_budget_policy"], budget_policy_warnings = resolve_core_budget_policy_for_month(
            merged_buy_rules["core_budget_policy"],
            review_target_month_start,
        )

    merged_tickers = deepcopy(tickers)
    if market_reference_path.exists():
        market_reference = load_yaml(market_reference_path)
        merged_tickers.setdefault("yfinance_symbols", {}).update(market_reference.get("yfinance_symbols", {}))

    merged_policy = deepcopy(portfolio_policy)
    if active_strategy is not None:
        merged_policy["active_strategy"] = active_strategy
        merged_policy["active_plans"] = active_plans
        merged_policy["long_term_thesis"] = load_thesis_monitoring_policy(
            project_root
        )
    if classification_overrides_path.exists():
        merged_policy["classification_overrides"] = load_yaml(classification_overrides_path)
    recurring_context = load_recurring_contribution_context(project_root)
    recurring_contributions = recurring_context["contributions"]
    recurring_contributions, recurring_contribution_warnings = resolve_core_recurring_contributions_for_month(
        recurring_contributions,
        review_target_month_start,
    )
    if active_strategy is not None:
        recurring_contribution_warnings.extend(
            build_recurring_strategy_alignment_warnings(
                recurring_contributions,
                active_strategy,
            )
        )
    pension_monthly_total_jpy = sum(
        int(item.get("amount_jpy_per_month", 0))
        for item in recurring_contributions.get("pension_monthly_dca", [])
    )
    annualized_pension_dca_jpy = pension_monthly_total_jpy * 12
    annualized_pension_dca_pct_of_total_assets = percent(
        Decimal(str(annualized_pension_dca_jpy)),
        snapshot.total_assets_jpy,
    )
    crypto_weekly_total_jpy = sum(
        int(item.get("amount_jpy_per_week", 0))
        for item in recurring_contributions.get("crypto_weekly_dca", [])
    )
    annualized_crypto_dca_jpy = crypto_weekly_total_jpy * 52
    annualized_crypto_dca_pct_of_total_assets = percent(
        Decimal(str(annualized_crypto_dca_jpy)),
        snapshot.total_assets_jpy,
    )
    recurring_contributions["pension_monthly_dca_total_jpy"] = pension_monthly_total_jpy
    recurring_contributions["annualized_pension_dca_jpy"] = annualized_pension_dca_jpy
    recurring_contributions["annualized_pension_dca_pct_of_total_assets"] = annualized_pension_dca_pct_of_total_assets
    recurring_contributions["crypto_weekly_dca_total_jpy"] = crypto_weekly_total_jpy
    recurring_contributions["annualized_crypto_dca_jpy"] = annualized_crypto_dca_jpy
    recurring_contributions["annualized_crypto_dca_pct_of_total_assets"] = annualized_crypto_dca_pct_of_total_assets

    portfolio_analysis = compute_portfolio_metrics(snapshot, merged_policy)
    requests = build_reference_requests(snapshot, merged_buy_rules, merged_tickers, portfolio_analysis["resolved_buckets"])
    market_references = fetch_market_references(requests)
    exposure_breakdown = build_exposure_breakdown(
        snapshot,
        merged_policy,
        portfolio_analysis["resolved_buckets"],
    )
    core_buy_materials, core_material_warnings = build_core_buy_materials(
        snapshot,
        portfolio_analysis["bucket_allocations"],
        portfolio_analysis["resolved_buckets"],
        market_references,
        merged_buy_rules,
        strategy_allocations=portfolio_analysis["strategy_allocations"],
        strategy_metrics=portfolio_analysis["strategy_metrics"],
        active_strategy=active_strategy,
        active_plans=active_plans,
    )
    raw_candidates = compute_candidate_metrics(
        snapshot,
        merged_buy_rules,
        merged_policy,
        market_references,
        portfolio_analysis["resolved_buckets"],
        portfolio_analysis["bucket_allocations"],
        mode_context={"portfolio_management_mode": core_buy_materials.get("portfolio_management_mode")},
    )
    candidate_orders, candidate_warnings = apply_candidate_validations(raw_candidates, merged_buy_rules)
    sox_buy_signal = calculate_sox_buy_signal(
        merged_buy_rules,
        market_references,
        bucket_allocations=portfolio_analysis["bucket_allocations"],
        exposure_breakdown=exposure_breakdown,
        active_strategy=active_strategy,
    )
    long_term_thesis_targets = build_long_term_thesis_targets(
        snapshot,
        merged_policy,
        portfolio_analysis["resolved_buckets"],
        portfolio_analysis["symbol_weights"],
    )
    security_story_targets = build_security_story_targets(
        snapshot,
        merged_policy.get("long_term_thesis", {}),
        holding_metadata,
    )
    core_spot_buy_materials = build_core_spot_buy_materials(
        snapshot=snapshot,
        portfolio_analysis=portfolio_analysis,
        core_buy_materials=core_buy_materials,
        market_references=market_references,
        recurring_contributions=recurring_contributions,
    )

    warnings = list(portfolio_analysis["warnings"])
    warnings.extend(candidate_warnings)
    warnings.extend(core_material_warnings)
    warnings.extend(recurring_contribution_warnings)
    warnings.extend(budget_policy_warnings)
    warnings.extend(build_exposure_validation_warnings(exposure_breakdown))
    warnings.extend(previous_snapshot_warnings)
    warnings.extend(
        build_snapshot_validation_warnings(
            snapshot,
            previous_snapshot=previous_snapshot,
            classification_audit=portfolio_analysis["classification_audit"],
        )
    )
    warnings.extend(build_validation_warnings(snapshot.warnings))
    if (
        active_strategy is not None
        and buy_rules.get("policy_status") == "legacy_analytical_heuristic"
    ):
        warnings.append(
            PortfolioWarning(
                code="legacy_candidate_heuristic_review_only",
                severity="info",
                message=(
                    "Limit-order candidates come from a legacy analytical heuristic, "
                    "not an approved order plan. They are review material only."
                ),
            )
        )
    core_reference_missing_symbols = sorted(
        {
            symbol
            for warning in core_material_warnings
            if warning.code in {"missing_core_market_reference", "missing_core_drawdown_reference"}
            for symbol in warning.related_symbols
        }
    )
    core_reference_proxy_suggestions = {
        item["symbol"]: item["suggested_proxy_symbol"]
        for item in core_buy_materials.get("core_constituents", [])
        if item.get("reference_symbol") is None and item.get("suggested_proxy_symbol") is not None
    }
    classification_override_count = sum(
        1
        for item in portfolio_analysis["classification_audit"]
        if item["raw_bucket"] != item["resolved_bucket"]
    )
    bucket_allocations_by_name = {allocation.bucket: allocation for allocation in portfolio_analysis["bucket_allocations"]}
    tradable_core_pct = (
        bucket_allocations_by_name["core"].actual_pct if "core" in bucket_allocations_by_name else None
    )
    pension_pct = (
        bucket_allocations_by_name["pension"].actual_pct if "pension" in bucket_allocations_by_name else Decimal("0")
    )
    effective_core_including_pension_pct = (
        quantize(tradable_core_pct + pension_pct, 4) if tradable_core_pct is not None else None
    )
    recurring_total_jpy = recurring_contributions.get("total_monthly_jpy")
    recommended_spot_buy_jpy = core_buy_materials.get("recommended_monthly_core_buy_budget_jpy")
    active_plan_account_type = core_buy_materials.get("active_plan_account_type")
    active_plan_id = core_buy_materials.get("active_plan_id")
    monthly_taxable_core_spot_buy_required = bool(
        recurring_contributions.get("taxable_core_spot_buy_required", False)
        or (
            active_plan_id
            and active_plan_account_type
            and "特定口座" in str(active_plan_account_type)
        )
    )
    monthly_total_core_deployment_jpy = (
        recurring_total_jpy + recommended_spot_buy_jpy
        if recurring_total_jpy is not None and recommended_spot_buy_jpy is not None
        else None
    )
    cash_normalization_months_estimate = estimate_cash_normalization_months(
        liquidity_allocation=bucket_allocations_by_name.get("liquidity"),
        total_assets_jpy=snapshot.total_assets_jpy,
        monthly_total_core_deployment_jpy=monthly_total_core_deployment_jpy,
        monthly_cash_inflow_jpy=(
            None
            if active_strategy is not None
            else LEGACY_ASSUMED_MONTHLY_CASH_INFLOW_JPY
        ),
    )
    quarterly_no_change = classification_override_count == 0 and not core_reference_missing_symbols
    return MonthlyComputation(
        snapshot=snapshot,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        bucket_allocations=portfolio_analysis["bucket_allocations"],
        market_references=market_references,
        candidate_orders=candidate_orders,
        warnings=warnings,
        semi_exposure_pct=exposure_breakdown["semiconductor_exposure_total_pct"],
        liquidity_jpy=portfolio_analysis["liquidity_jpy"],
        sox_buy_signal=sox_buy_signal,
        strategy_allocations=portfolio_analysis["strategy_allocations"],
        strategy_summary={
            "strategy_id": (active_strategy or {}).get("strategy_id"),
            "effective_from": (active_strategy or {}).get("effective_from"),
            "reserved_hobby_cash_jpy": portfolio_analysis["strategy_metrics"].get(
                "recognized_reserved_cash_jpy"
            ),
            "unallocated_liquidity_jpy": portfolio_analysis["strategy_metrics"].get(
                "unallocated_liquidity_jpy"
            ),
            "residual_jpy": portfolio_analysis["strategy_metrics"].get("residual_jpy"),
            "active_plan_ids": [
                plan.get("plan_id")
                for plan in active_plans
                if plan.get("plan_id") is not None
            ],
        },
        portfolio_summary=portfolio_analysis["portfolio_summary"],
        core_buy_materials=core_buy_materials,
        exposure_breakdown=exposure_breakdown,
        long_term_thesis_targets=long_term_thesis_targets,
        security_story_targets=security_story_targets,
        monthly_execution_outputs={
            "review_target_month": review_target_month,
            "nisa_growth_quota_status": recurring_contributions.get("nisa_growth_quota_status"),
            "fixed_core_auto_invest_amount_jpy": recurring_total_jpy,
            "taxable_core_spot_buy_required": monthly_taxable_core_spot_buy_required,
            "recommended_taxable_core_spot_buy_jpy": (
                recommended_spot_buy_jpy
                if monthly_taxable_core_spot_buy_required
                else None
            ),
            "core_spot_buy_account_type": (
                active_plan_account_type
                or recurring_contributions.get("core_spot_buy_account_type")
            ),
            "portfolio_management_mode": core_buy_materials.get("portfolio_management_mode"),
            "monthly_core_budget_tier": core_buy_materials.get("monthly_core_budget_tier"),
            "recommended_monthly_core_buy_budget_jpy": core_buy_materials.get(
                "recommended_monthly_core_buy_budget_jpy"
            ),
            "monthly_total_core_deployment_jpy": monthly_total_core_deployment_jpy,
            "candidate_count": len(candidate_orders),
            "core_recurring_contributions_total_jpy": recurring_contributions.get("total_monthly_jpy"),
            "pension_monthly_dca_total_jpy": pension_monthly_total_jpy,
            "annualized_pension_dca_jpy": annualized_pension_dca_jpy,
            "annualized_pension_dca_pct_of_total_assets": annualized_pension_dca_pct_of_total_assets,
            "crypto_weekly_dca_total_jpy": crypto_weekly_total_jpy,
            "annualized_crypto_dca_jpy": annualized_crypto_dca_jpy,
            "annualized_crypto_dca_pct_of_total_assets": annualized_crypto_dca_pct_of_total_assets,
            "taxable_account_note": recurring_contributions.get("taxable_account_note"),
            "nisa_exhaustion_adjustment_reason": recurring_contributions.get(
                "nisa_exhaustion_adjustment_reason"
            ),
        },
        quarterly_rule_review_outputs={
            "no_change": quarterly_no_change,
            "classification_override_count": classification_override_count,
            "classification_audit": portfolio_analysis["classification_audit"],
            "core_reference_missing_symbols": core_reference_missing_symbols,
            "core_reference_proxy_suggestions": core_reference_proxy_suggestions,
            "tradable_core_pct": tradable_core_pct,
            "effective_core_including_pension_pct": effective_core_including_pension_pct,
            "cash_normalization_months_estimate": cash_normalization_months_estimate,
            "direct_semiconductor_exposure_pct": exposure_breakdown.get("direct_semiconductor_exposure_pct"),
            "combined_semiconductor_ai_infra_watch_pct": exposure_breakdown.get(
                "combined_semiconductor_ai_infra_watch_pct"
            ),
            "indirect_ai_infra_exposure_pct": exposure_breakdown.get("indirect_ai_infra_exposure_pct"),
        },
        metadata={
            "snapshot_path": str(snapshot_path),
            "previous_snapshot_path": str(previous_snapshot_path(snapshot_path, review_target_month_start))
            if previous_snapshot is not None
            else None,
            "review_target_month": review_target_month,
            "review_target_month_start": review_target_month_start.isoformat(),
            "strategy_id": (active_strategy or {}).get("strategy_id"),
            "strategy_effective_from": (active_strategy or {}).get("effective_from"),
            "approved_review_constraints": build_approved_review_constraints(
                active_strategy
            ),
            "active_strategy_path": strategy_context.get("pointer", {}).get(
                "active_strategy_path"
            ),
            "active_plan_paths": strategy_context.get("pointer", {}).get(
                "active_plan_paths",
                [],
            ),
            "resolved_buckets": portfolio_analysis["resolved_buckets"],
            "classification_audit": portfolio_analysis["classification_audit"],
            "core_recurring_contributions": recurring_contributions,
            "core_recurring_contributions_source": recurring_context["source_path"],
            "holding_metadata_source": holding_context["source_path"],
            "holding_metadata_effective_from": holding_context["record"].get(
                "effective_from"
            ),
            "holding_execution_context": holding_context["record"].get(
                "execution_context", {}
            ),
            "current_state_projection": current_state_projection,
            "satellite_review_policy": deepcopy(
                (active_strategy or {})
                .get("review_policy", {})
                .get("satellite_parameters", {})
            ),
            "tactical_cash_policy": deepcopy(
                (active_strategy or {})
                .get("allocation", {})
                .get("tactical_cash", {})
            ),
            "review_output_policy": deepcopy(
                (active_strategy or {})
                .get("review_policy", {})
                .get("output_contract", {})
            ),
            "candidate_policy_status": buy_rules.get("policy_status"),
            "core_spot_buy_materials": core_spot_buy_materials,
        },
    )


def build_approved_review_constraints(active_strategy: dict | None) -> list[dict]:
    if not active_strategy:
        return []
    semiconductor = (
        active_strategy.get("risk_limits", {})
        .get("direct_themes", {})
        .get("semiconductor", {})
    )
    target_pct = semiconductor.get("rebalance_proposal_above_pct")
    approval_ref = semiconductor.get("approval_ref")
    if target_pct is None or not approval_ref:
        return []
    return [
        {
            "condition_id": "approved_direct_semiconductor_max_pct",
            "statement": (
                "直接半導体エクスポージャーを総資産の"
                f"{Decimal(str(target_pct)) * 100}%以下へ縮小する方針にユーザが同意済み。"
                "売却対象の優先順位は独立レビューから提案を受ける"
            ),
            "source": str(approval_ref),
            "as_of": str(active_strategy.get("effective_from") or "unknown"),
            "status": "confirmed",
            "upper_bound_pct": Decimal(str(target_pct)) * 100,
            "denominator": "household_total_assets_jpy",
        }
    ]


def load_previous_snapshot_for_validation(
    snapshot_path: Path,
    review_target_month_start: date,
) -> tuple[PortfolioSnapshot | None, list[PortfolioWarning]]:
    candidate_path = previous_snapshot_path(snapshot_path, review_target_month_start)
    if candidate_path == snapshot_path or not candidate_path.exists():
        return None, []
    try:
        return load_snapshot(candidate_path), []
    except Exception as exc:  # noqa: BLE001
        return None, [
            PortfolioWarning(
                code="previous_snapshot_validation_unavailable",
                severity="warning",
                message=f"Could not load previous snapshot for snapshot continuity validation: {candidate_path} ({exc})",
            )
        ]


def previous_snapshot_path(snapshot_path: Path, review_target_month_start: date) -> Path:
    previous_month = previous_month_start(review_target_month_start)
    return snapshot_path.parent / f"snapshot_{previous_month.strftime('%Y_%m')}.yaml"


def previous_month_start(value: date) -> date:
    year = value.year - 1 if value.month == 1 else value.year
    month = 12 if value.month == 1 else value.month - 1
    return date(year, month, 1)


def estimate_cash_normalization_months(
    *,
    liquidity_allocation,
    total_assets_jpy: Decimal,
    monthly_total_core_deployment_jpy,
    monthly_cash_inflow_jpy: Decimal | None,
):
    if liquidity_allocation is None or liquidity_allocation.target_pct is None:
        return None
    if monthly_total_core_deployment_jpy in (None, 0):
        return None
    cash_excess_pct = liquidity_allocation.actual_pct - liquidity_allocation.target_pct
    if cash_excess_pct <= 0:
        return {
            "gross_deployment_months": Decimal("0.0"),
            "net_cash_reduction_months": Decimal("0.0"),
            "assumed_monthly_cash_inflow_jpy": monthly_cash_inflow_jpy,
            "net_cash_reduction_jpy": Decimal("0"),
        }
    cash_excess_jpy = total_assets_jpy * cash_excess_pct
    gross_deployment_months = quantize(cash_excess_jpy / Decimal(str(monthly_total_core_deployment_jpy)), 1)
    net_cash_reduction_jpy = Decimal(str(monthly_total_core_deployment_jpy))
    if monthly_cash_inflow_jpy is not None:
        net_cash_reduction_jpy = net_cash_reduction_jpy - monthly_cash_inflow_jpy
    net_cash_reduction_months = None
    if net_cash_reduction_jpy > 0:
        net_cash_reduction_months = quantize(cash_excess_jpy / net_cash_reduction_jpy, 1)
    return {
        "gross_deployment_months": gross_deployment_months,
        "net_cash_reduction_months": net_cash_reduction_months,
        "assumed_monthly_cash_inflow_jpy": monthly_cash_inflow_jpy,
        "net_cash_reduction_jpy": net_cash_reduction_jpy,
    }


def resolve_core_budget_policy_for_month(
    budget_policy: dict,
    review_target_month_start: date,
) -> tuple[dict, list[PortfolioWarning]]:
    resolved = deepcopy(budget_policy)
    overrides = resolved.pop("date_based_overrides", []) or []
    active_override = find_active_month_override(overrides, review_target_month_start)
    if active_override is None:
        resolved["date_based_override_active"] = False
        return resolved, []

    resolved = deep_merge_dicts(resolved, active_override)
    resolved.pop("date_based_overrides", None)
    resolved["date_based_override_active"] = True
    resolved["active_date_based_override"] = summarize_date_based_override(active_override)
    return resolved, []


def resolve_core_recurring_contributions_for_month(
    recurring_contributions: dict,
    review_target_month_start: date,
) -> tuple[dict, list[PortfolioWarning]]:
    resolved = deepcopy(recurring_contributions)
    overrides = resolved.pop("date_based_overrides", []) or []
    active_override = find_active_month_override(overrides, review_target_month_start)
    warnings: list[PortfolioWarning] = []
    if active_override is not None:
        base_review_guidance = list(resolved.get("review_guidance", []) or [])
        override_review_guidance = list(active_override.get("review_guidance", []) or [])
        resolved = deep_merge_dicts(resolved, active_override)
        resolved.pop("date_based_overrides", None)
        if override_review_guidance:
            resolved["review_guidance"] = base_review_guidance + override_review_guidance
        resolved["date_based_override_active"] = True
        resolved["active_date_based_override"] = summarize_date_based_override(active_override)
        return resolved, warnings

    resolved["date_based_override_active"] = False
    latest_followup_override = latest_followup_required_override(overrides)
    if latest_followup_override is not None:
        latest_end = parse_month_start(latest_followup_override["active_to"])
        if review_target_month_start > latest_end:
            code = str(
                latest_followup_override.get(
                    "followup_warning_code",
                    "post_date_based_core_recurring_rule_missing",
                )
            )
            message = (
                f"No explicit core recurring contribution / NISA growth quota rule is configured for "
                f"{review_target_month_start.strftime('%Y_%m')}; do not carry the "
                f"{latest_followup_override.get('active_from')} to {latest_followup_override.get('active_to')} "
                "override forward without configuration."
            )
            warnings.append(PortfolioWarning(code=code, severity="warning", message=message))
            resolved["configuration_warnings"] = [message]
            resolved["nisa_growth_quota_status"] = "requires_explicit_configuration"
    return resolved, warnings


def build_recurring_strategy_alignment_warnings(
    recurring_contributions: dict,
    active_strategy: dict,
) -> list[PortfolioWarning]:
    existing_sp500_policy = active_strategy.get("core_policy", {}).get(
        "existing_sp500",
        {},
    )
    if existing_sp500_policy.get("new_routine_purchase") is not False:
        return []

    conflicting_plans = [
        plan
        for plan in recurring_contributions.get("plans", [])
        if "S&P500" in str(plan.get("fund_name", "")).upper()
        and int(plan.get("amount_jpy", 0)) > 0
    ]
    if not conflicting_plans:
        return []

    return [
        PortfolioWarning(
            code="core_recurring_plan_conflicts_with_current_strategy",
            severity="warning",
            message=(
                "The recorded recurring plan still buys S&P500, while the active strategy "
                "routes new broad-core purchases to all-country only. Treat the recurring plan "
                "as an observed fact until the user changes it; do not silently mark it updated."
            ),
            related_symbols=[
                str(plan.get("fund_name"))
                for plan in conflicting_plans
            ],
        )
    ]


def find_active_month_override(overrides: list[dict], review_target_month_start: date) -> dict | None:
    for override in overrides:
        active_from = override.get("active_from") or override.get("period", {}).get("start")
        active_to = override.get("active_to") or override.get("period", {}).get("end")
        if active_from is None or active_to is None:
            continue
        start = parse_month_start(active_from)
        end = parse_month_start(active_to)
        if start <= review_target_month_start <= end:
            return override
    return None


def latest_followup_required_override(overrides: list[dict]) -> dict | None:
    candidates = [
        override
        for override in overrides
        if override.get("requires_explicit_followup_rule") and override.get("active_to") is not None
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda override: parse_month_start(override["active_to"]))


def parse_month_start(value) -> date:
    if isinstance(value, date):
        return date(value.year, value.month, 1)
    parts = str(value).replace("_", "-").split("-")
    if len(parts) < 2:
        raise ValueError(f"Invalid month value: {value}")
    return date(int(parts[0]), int(parts[1]), 1)


def deep_merge_dicts(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if key in {"active_from", "active_to", "period"}:
            merged[key] = deepcopy(value)
            continue
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def summarize_date_based_override(override: dict) -> dict:
    omitted_keys = {"plans", "review_guidance"}
    return {key: deepcopy(value) for key, value in override.items() if key not in omitted_keys}


def build_reference_requests(
    snapshot,
    buy_rules: dict,
    tickers: dict,
    resolved_buckets: dict[str, str],
) -> dict[str, dict[str, str]]:
    yfinance_symbols = tickers.get("yfinance_symbols", {})
    required_symbols = list(buy_rules.get("limit_order_rules", {}).keys())
    proxy_symbol = buy_rules.get("sox_buy_judgement", {}).get("proxy_symbol")
    if proxy_symbol and proxy_symbol not in required_symbols:
        required_symbols.append(proxy_symbol)
    required_symbols.append("USDJPY")

    optional_core_symbols = [
        holding
        for holding in snapshot.holdings
        if resolved_buckets.get(holding.symbol) == "core"
    ]

    requests: dict[str, dict[str, str]] = {}
    for symbol in required_symbols:
        lookup_key = symbol if symbol != "USDJPY" else "USDJPY"
        yfinance_symbol = yfinance_symbols.get(lookup_key)
        if yfinance_symbol is None:
            raise ValueError(f"No yfinance symbol configured for {symbol}")
        requests[symbol] = {
            "yfinance_symbol": yfinance_symbol,
            "currency": "JPY" if symbol == "USDJPY" else "USD",
        }
    for holding in optional_core_symbols:
        symbol = holding.symbol
        if symbol in requests:
            continue
        yfinance_symbol = yfinance_symbols.get(symbol) or suggest_core_proxy_symbol(holding)
        if yfinance_symbol is None:
            continue
        requests[symbol] = {
            "yfinance_symbol": yfinance_symbol,
            "currency": "USD",
        }
    return requests


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_applicable_strategy_context(
    project_root: Path,
    review_target_month_start: date,
) -> dict:
    pointer_path = project_root / "strategy/current.yaml"
    if not pointer_path.exists():
        return {"pointer": {}, "strategy": None, "active_plans": []}

    context = load_current_strategy_context(project_root)
    effective_from = date.fromisoformat(str(context["strategy"]["effective_from"]))
    effective_month = date(effective_from.year, effective_from.month, 1)
    if review_target_month_start < effective_month:
        return {
            "pointer": context["pointer"],
            "strategy": None,
            "active_plans": [],
        }
    return context


def build_core_spot_buy_materials(
    *,
    snapshot,
    portfolio_analysis: dict,
    core_buy_materials: dict,
    market_references: list,
    recurring_contributions: dict,
) -> dict:
    allocation_map = {allocation.bucket: allocation for allocation in portfolio_analysis["bucket_allocations"]}
    strategy_allocation_map = {
        allocation.bucket: allocation
        for allocation in portfolio_analysis.get("strategy_allocations", [])
    }
    reference_map = {reference.symbol: reference for reference in market_references}
    current_monthly_core_auto_invest = recurring_contributions.get("total_monthly_jpy")
    fixed_core_auto_invest = recurring_contributions.get(
        "monthly_core_auto_invest_amount_jpy",
        current_monthly_core_auto_invest,
    )
    recommended_core_spot_buy = core_buy_materials.get("recommended_monthly_core_buy_budget_jpy")
    active_plan_account_type = core_buy_materials.get("active_plan_account_type")
    active_plan_id = core_buy_materials.get("active_plan_id")
    taxable_core_spot_buy_required = bool(
        recurring_contributions.get("taxable_core_spot_buy_required", False)
        or (
            active_plan_id
            and active_plan_account_type
            and "特定口座" in str(active_plan_account_type)
        )
    )
    total_monthly_core_deployment = (
        fixed_core_auto_invest + recommended_core_spot_buy
        if fixed_core_auto_invest is not None and recommended_core_spot_buy is not None
        else None
    )
    annualized_core_auto_invest = (
        int(current_monthly_core_auto_invest) * 12 if current_monthly_core_auto_invest is not None else None
    )
    liquidity_jpy = portfolio_analysis["liquidity_jpy"]

    major_core_proxy_stats: list[dict] = []
    seen_reference_symbols: set[str] = set()
    for constituent in core_buy_materials.get("core_constituents", []):
        reference_symbol = constituent.get("reference_symbol")
        symbol = constituent.get("symbol")
        reference = reference_map.get(symbol)
        if reference_symbol is None or reference is None or reference_symbol in seen_reference_symbols:
            continue
        seen_reference_symbols.add(reference_symbol)
        major_core_proxy_stats.append(
            {
                "reference_symbol": reference_symbol,
                "one_month_return_pct": percent_change(reference.current_price, reference.prior_close_21d),
                "three_month_return_pct": percent_change(reference.current_price, reference.prior_close_63d),
                "one_month_drawdown_from_high_pct": drawdown_pct(reference.current_price, reference.recent_high_21d),
                "three_month_drawdown_from_high_pct": drawdown_pct(reference.current_price, reference.recent_high_63d),
            }
        )

    jun_core_allocation = allocation_map.get("jun_core")
    bond_like_holdings = detect_bond_like_holdings(snapshot.holdings)
    real_estate_risk_profile = build_real_estate_risk_profile()
    if active_plan_id:
        core_spot_buy_allocation_rule = {
            "source_role": "approved_active_plan",
            "target_group": core_buy_materials.get("active_plan_target_group"),
            "product": core_buy_materials.get("active_plan_product"),
            "product_allocation_pct": core_buy_materials.get(
                "active_plan_product_allocation_pct"
            ),
        }
        baseline_total_core_deployment_target_jpy = None
        baseline_core_spot_buy_jpy = None
        date_based_override_active = False
        active_date_based_override = None
    else:
        core_spot_buy_allocation_rule = recurring_contributions.get(
            "core_spot_buy_allocation_rule"
        )
        baseline_total_core_deployment_target_jpy = (
            recurring_contributions.get("baseline_total_core_deployment_target_jpy")
            or core_buy_materials.get("baseline_total_core_deployment_target_jpy")
        )
        baseline_core_spot_buy_jpy = (
            core_buy_materials.get("baseline_core_spot_buy_jpy")
            or recurring_contributions.get(
                "rebalance_mode_core_spot_buy_reference_jpy"
            )
        )
        date_based_override_active = recurring_contributions.get(
            "date_based_override_active",
            False,
        )
        active_date_based_override = recurring_contributions.get(
            "active_date_based_override"
        )
    return {
        "strategy_id": core_buy_materials.get("strategy_id"),
        "active_plan_id": core_buy_materials.get("active_plan_id"),
        "active_plan_status": core_buy_materials.get("active_plan_status"),
        "active_plan_account_type": core_buy_materials.get("active_plan_account_type"),
        "active_plan_execution_amount_rule": core_buy_materials.get(
            "active_plan_execution_amount_rule"
        ),
        "active_plan_target_group": core_buy_materials.get("active_plan_target_group"),
        "active_plan_product": core_buy_materials.get("active_plan_product"),
        "active_plan_product_allocation_pct": core_buy_materials.get(
            "active_plan_product_allocation_pct"
        ),
        "active_plan_execution_method": core_buy_materials.get(
            "active_plan_execution_method"
        ),
        "active_plan_requires_pretrade_balance_confirmation": core_buy_materials.get(
            "active_plan_requires_pretrade_balance_confirmation"
        ),
        "active_plan_user_executes_order_manually": core_buy_materials.get(
            "active_plan_user_executes_order_manually"
        ),
        "broad_core_actual_pct": (
            strategy_allocation_map["broad_core"].actual_pct
            if "broad_core" in strategy_allocation_map
            else None
        ),
        "broad_core_target_pct": (
            strategy_allocation_map["broad_core"].target_pct
            if "broad_core" in strategy_allocation_map
            else None
        ),
        "active_hobby_actual_pct": (
            strategy_allocation_map["active_hobby"].actual_pct
            if "active_hobby" in strategy_allocation_map
            else None
        ),
        "active_hobby_target_pct": (
            strategy_allocation_map["active_hobby"].target_pct
            if "active_hobby" in strategy_allocation_map
            else None
        ),
        "reserved_hobby_cash_jpy": core_buy_materials.get("reserved_hobby_cash_jpy"),
        "unallocated_liquidity_jpy": core_buy_materials.get("unallocated_liquidity_jpy"),
        "liquidity_actual_pct": core_buy_materials.get("liquidity_actual_pct"),
        "liquidity_target_pct": core_buy_materials.get("liquidity_target_pct"),
        "cash_excess_pct": core_buy_materials.get("cash_excess_pct"),
        "core_actual_pct": core_buy_materials.get("core_actual_pct"),
        "core_target_pct": core_buy_materials.get("core_target_pct"),
        "core_delta_pct": core_buy_materials.get("core_delta_pct"),
        "jun_core_actual_pct": jun_core_allocation.actual_pct if jun_core_allocation is not None else None,
        "jun_core_target_pct": jun_core_allocation.target_pct if jun_core_allocation is not None else None,
        "jun_core_delta_pct": jun_core_allocation.delta_pct if jun_core_allocation is not None else None,
        "nisa_growth_quota_status": recurring_contributions.get("nisa_growth_quota_status"),
        "nisa_exhaustion_adjustment_reason": recurring_contributions.get("nisa_exhaustion_adjustment_reason"),
        "taxable_core_spot_buy_required": taxable_core_spot_buy_required,
        "core_spot_buy_account_type": (
            active_plan_account_type
            or recurring_contributions.get("core_spot_buy_account_type")
        ),
        "taxable_account_note": recurring_contributions.get("taxable_account_note"),
        "tax_note": recurring_contributions.get("tax_note"),
        "fixed_core_auto_invest_amount_jpy": fixed_core_auto_invest,
        "current_monthly_core_auto_invest_amount_jpy": current_monthly_core_auto_invest,
        "annualized_core_auto_invest_amount_jpy": annualized_core_auto_invest,
        "recommended_taxable_core_spot_buy_jpy": (
            recommended_core_spot_buy if taxable_core_spot_buy_required else None
        ),
        "recommended_monthly_core_buy_budget_jpy": recommended_core_spot_buy,
        "total_monthly_core_deployment_jpy": total_monthly_core_deployment,
        "baseline_total_core_deployment_target_jpy": baseline_total_core_deployment_target_jpy,
        "baseline_core_spot_buy_jpy": baseline_core_spot_buy_jpy,
        "hard_cap_core_spot_buy_jpy": core_buy_materials.get("hard_cap_core_spot_buy_jpy"),
        "monthly_core_budget_band": core_buy_materials.get("monthly_core_budget_band"),
        "spot_buy_bands": core_buy_materials.get("spot_buy_bands"),
        "core_spot_buy_allocation_rule": core_spot_buy_allocation_rule,
        "date_based_override_active": date_based_override_active,
        "active_date_based_override": active_date_based_override,
        "configuration_warnings": recurring_contributions.get("configuration_warnings", []),
        "major_core_proxy_stats": major_core_proxy_stats,
        "portfolio_risk_bucket_summary": [
            {
                "bucket": allocation.bucket,
                "actual_pct": allocation.actual_pct,
                "target_pct": allocation.target_pct,
                "delta_pct": allocation.delta_pct,
            }
            for allocation in portfolio_analysis["bucket_allocations"]
        ],
        "current_cash_jpy": liquidity_jpy,
        "bond_like_holdings_present": bool(bond_like_holdings),
        "bond_like_holdings": bond_like_holdings or None,
        "emergency_fund_managed_separately": None,
        "near_term_large_expense": None,
        "real_estate_exposure_present": real_estate_risk_profile["real_estate_exposure_present"],
        "real_estate_use": real_estate_risk_profile["real_estate_use"],
        "mortgage_status": real_estate_risk_profile["mortgage_status"],
        "liquidity_comment": real_estate_risk_profile["liquidity_comment"],
    }


def percent_change(current_value, prior_value):
    if current_value in (None, 0) or prior_value in (None, 0):
        return None
    return quantize((current_value - prior_value) / prior_value * 100, 2)


def drawdown_pct(current_value, high_value):
    if current_value in (None, 0) or high_value in (None, 0):
        return None
    return quantize((current_value - high_value) / high_value * 100, 2)


def detect_bond_like_holdings(holdings) -> list[dict]:
    keywords = ("bond", "債券", "mmf", "国債", "treasury")
    matches: list[dict] = []
    for holding in holdings:
        symbol = str(holding.symbol).lower()
        name = str(holding.name).lower()
        if any(keyword in symbol or keyword in name for keyword in keywords):
            matches.append(
                {
                    "symbol": holding.symbol,
                    "name": holding.name,
                    "market_value_jpy": holding.market_value_jpy,
                }
            )
    return matches


def build_real_estate_risk_profile() -> dict[str, object]:
    return {
        "real_estate_exposure_present": True,
        "real_estate_use": "residence_and_asset",
        "mortgage_status": "full_loan_early_stage",
        "liquidity_comment": "residential real estate should not be treated as emergency liquidity",
    }


if __name__ == "__main__":
    sys.exit(main())
