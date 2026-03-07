from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from .codex_patch_builder import build_codex_patch_prompt, build_codex_patch_request
from .diff_analyzer import build_proposal_diffs
from .market_data import fetch_market_references
from .models import MonthlyComputation, PortfolioWarning
from .portfolio import analyze_portfolio
from .prompt_builder import build_monthly_review_prompt
from .review_parser import parse_review_feedback
from .rules import calculate_candidate_orders, calculate_sox_buy_signal
from .snapshot_loader import load_snapshot
from .storage import default_output_paths, load_yaml, read_text, write_text, write_yaml
from .utils import month_key

LOGGER = logging.getLogger(__name__)


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
    parser = argparse.ArgumentParser(description="Monthly limit-order review CLI")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    review_parser = subparsers.add_parser("generate-review-prompt", help="Generate monthly ChatGPT review prompt")
    review_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    review_parser.add_argument("--output", required=False, help="Path to output markdown prompt")
    review_parser.set_defaults(func=handle_generate_review_prompt)

    ingest_parser = subparsers.add_parser("ingest-review", help="Ingest a ChatGPT review text file")
    ingest_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    ingest_parser.add_argument("--review-text", required=True, help="Path to saved ChatGPT review text")
    ingest_parser.set_defaults(func=handle_ingest_review)

    codex_parser = subparsers.add_parser("generate-codex-patch", help="Generate a Codex patch prompt")
    codex_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    codex_parser.add_argument("--review-text", required=True, help="Path to saved ChatGPT review text")
    codex_parser.add_argument("--output", required=False, help="Path to output markdown prompt")
    codex_parser.set_defaults(func=handle_generate_codex_patch)

    monthly_parser = subparsers.add_parser("monthly-run", help="Run monthly computation and prompt generation")
    monthly_parser.add_argument("--snapshot", required=True, help="Path to normalized snapshot YAML")
    monthly_parser.set_defaults(func=handle_monthly_run)
    return parser


def configure_logging(*, verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )


def handle_generate_review_prompt(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    computation = compute_monthly(Path(args.snapshot), project_root=project_root)
    paths = default_output_paths(project_root, month_key(computation.snapshot.snapshot_date))
    output_path = Path(args.output) if args.output else paths["review_prompt"]
    template_text = read_text(project_root / "prompts/templates/monthly_review_template.md")
    prompt = build_monthly_review_prompt(computation, template_text)

    write_yaml(paths["computation"], computation)
    write_text(output_path, prompt)
    write_text(paths["review_prompt_history"], prompt)
    LOGGER.info("Saved computation to %s", paths["computation"])
    LOGGER.info("Saved review prompt to %s", output_path)
    return 0


def handle_ingest_review(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    computation = compute_monthly(Path(args.snapshot), project_root=project_root)
    review_text = read_text(args.review_text)
    review_feedback = parse_review_feedback(review_text)
    diffs = build_proposal_diffs(computation.candidate_orders, review_feedback, computation.warnings)
    paths = default_output_paths(project_root, month_key(computation.snapshot.snapshot_date))

    write_yaml(paths["computation"], computation)
    write_yaml(paths["review_structured"], review_feedback)
    write_yaml(paths["diff"], diffs)
    LOGGER.info("Saved structured review to %s", paths["review_structured"])
    LOGGER.info("Saved proposal diffs to %s", paths["diff"])
    return 0


def handle_generate_codex_patch(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    computation = compute_monthly(Path(args.snapshot), project_root=project_root)
    review_text = read_text(args.review_text)
    review_feedback = parse_review_feedback(review_text)
    diffs = build_proposal_diffs(computation.candidate_orders, review_feedback, computation.warnings)
    month = month_key(computation.snapshot.snapshot_date)
    patch_request = build_codex_patch_request(month, review_feedback, diffs)
    paths = default_output_paths(project_root, month)
    output_path = Path(args.output) if args.output else paths["patch_prompt"]
    template_text = read_text(project_root / "prompts/templates/codex_patch_template.md")
    prompt = build_codex_patch_prompt(template_text, patch_request, diffs)

    write_yaml(paths["computation"], computation)
    write_yaml(paths["review_structured"], review_feedback)
    write_yaml(paths["diff"], diffs)
    write_yaml(paths["patch_request"], patch_request)
    write_text(output_path, prompt)
    LOGGER.info("Saved Codex patch request to %s", paths["patch_request"])
    LOGGER.info("Saved Codex patch prompt to %s", output_path)
    return 0


def handle_monthly_run(args: argparse.Namespace) -> int:
    project_root = get_project_root()
    computation = compute_monthly(Path(args.snapshot), project_root=project_root)
    paths = default_output_paths(project_root, month_key(computation.snapshot.snapshot_date))
    template_text = read_text(project_root / "prompts/templates/monthly_review_template.md")
    prompt = build_monthly_review_prompt(computation, template_text)
    write_yaml(paths["computation"], computation)
    write_text(paths["review_prompt"], prompt)
    write_text(paths["review_prompt_history"], prompt)
    LOGGER.info("Saved computation to %s", paths["computation"])
    LOGGER.info("Saved review prompt to %s", paths["review_prompt"])
    return 0


def compute_monthly(snapshot_path: Path, *, project_root: Path) -> MonthlyComputation:
    snapshot = load_snapshot(snapshot_path)
    buy_rules = load_yaml(project_root / "config/buy_rules.yaml")
    portfolio_policy = load_yaml(project_root / "config/portfolio_policy.yaml")
    tickers = load_yaml(project_root / "config/tickers.yaml")

    portfolio_analysis = analyze_portfolio(snapshot, portfolio_policy)
    requests = build_reference_requests(buy_rules, tickers)
    market_references = fetch_market_references(requests)
    candidate_orders = calculate_candidate_orders(
        snapshot,
        buy_rules,
        portfolio_policy,
        market_references,
        liquidity_jpy=portfolio_analysis["liquidity_jpy"],
        symbol_weights=portfolio_analysis["symbol_weights"],
    )
    sox_buy_signal = calculate_sox_buy_signal(buy_rules, market_references)

    warnings = list(portfolio_analysis["warnings"])
    warnings.extend(
        PortfolioWarning(code="snapshot_warning", severity="info", message=message)
        for message in snapshot.warnings
    )
    return MonthlyComputation(
        snapshot=snapshot,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        bucket_allocations=portfolio_analysis["bucket_allocations"],
        market_references=market_references,
        candidate_orders=candidate_orders,
        warnings=warnings,
        semi_exposure_pct=portfolio_analysis["semi_exposure_pct"],
        liquidity_jpy=portfolio_analysis["liquidity_jpy"],
        sox_buy_signal=sox_buy_signal,
        metadata={
            "snapshot_path": str(snapshot_path),
            "resolved_buckets": portfolio_analysis["resolved_buckets"],
        },
    )


def build_reference_requests(buy_rules: dict, tickers: dict) -> dict[str, dict[str, str]]:
    yfinance_symbols = tickers.get("yfinance_symbols", {})
    request_symbols = list(buy_rules.get("limit_order_rules", {}).keys())
    proxy_symbol = buy_rules.get("sox_buy_judgement", {}).get("proxy_symbol")
    if proxy_symbol and proxy_symbol not in request_symbols:
        request_symbols.append(proxy_symbol)
    request_symbols.append("USDJPY")

    requests: dict[str, dict[str, str]] = {}
    for symbol in request_symbols:
        lookup_key = symbol if symbol != "USDJPY" else "USDJPY"
        yfinance_symbol = yfinance_symbols.get(lookup_key)
        if yfinance_symbol is None:
            raise ValueError(f"No yfinance symbol configured for {symbol}")
        requests[symbol] = {
            "yfinance_symbol": yfinance_symbol,
            "currency": "JPY" if symbol == "USDJPY" else "USD",
        }
    return requests


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


if __name__ == "__main__":
    sys.exit(main())
