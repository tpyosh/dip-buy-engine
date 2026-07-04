from __future__ import annotations

import re
from datetime import date

from .models import (
    CoreSpotBuyAllocation,
    CoreSpotBuyScheduleItem,
    ReviewCoreSpotBuyPlan,
    ReviewFeedback,
    ReviewOrderProposal,
)
from .utils import to_optional_decimal

SECTION_HEADINGS = {
    "core_spot_buy": ["今月のcoreスポット買い提案", "今月のCoreスポット買い提案"],
    "monthly_proposals": ["今月の指値提案", "指値提案"],
    "sox_decision": ["SOX投信判定", "SOX判定"],
    "portfolio_diagnosis": ["ポートフォリオ診断", "資産配分診断"],
    "rule_review": ["四半期ルール見直し", "ルール改善レビュー", "改善レビュー"],
    "codex_summary": ["Codex向け修正要約", "Codex 向け修正要約", "修正要約"],
}


def parse_review_feedback(review_text: str, *, review_target_month: str | None = None) -> ReviewFeedback:
    sections = split_sections(review_text)
    parser_warnings = [
        f"Section not found: {section_name}"
        for section_name in SECTION_HEADINGS
        if not sections.get(section_name)
    ]
    monthly_text = sections.get("monthly_proposals", "")
    codex_text = sections.get("codex_summary", "")

    must, should, nice_to_have = extract_priority_lists(codex_text)
    if not any([must, should, nice_to_have]):
        parser_warnings.append("Priority lists were not extracted from Codex summary.")

    target_month_start = parse_review_target_month(review_target_month) or infer_review_target_month_from_text(
        review_text
    )
    core_spot_buy_plan = extract_core_spot_buy_plan(
        sections.get("core_spot_buy", ""),
        target_month_start=target_month_start,
    )
    if core_spot_buy_plan is not None:
        parser_warnings.extend(core_spot_buy_plan.parser_warnings)

    return ReviewFeedback(
        raw_text=review_text,
        sections=sections,
        order_proposals=extract_order_proposals(monthly_text),
        sox_decision=extract_sox_decision(sections.get("sox_decision", "")),
        portfolio_diagnosis=extract_bullets(sections.get("portfolio_diagnosis", "")),
        rule_review=extract_bullets(sections.get("rule_review", "")),
        must=must,
        should=should,
        nice_to_have=nice_to_have,
        core_spot_buy_plan=core_spot_buy_plan,
        parser_warnings=parser_warnings,
    )


def split_sections(review_text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {name: [] for name in SECTION_HEADINGS}
    current: str | None = None
    for raw_line in review_text.splitlines():
        line = raw_line.rstrip()
        heading = detect_heading(line)
        if heading is not None:
            current = heading
            continue
        if is_untracked_heading(line):
            current = None
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def detect_heading(line: str) -> str | None:
    normalized = line.strip().lstrip("#").strip()
    normalized = normalized.strip("【】").strip()
    for canonical_name, candidates in SECTION_HEADINGS.items():
        for candidate in candidates:
            if normalized.startswith(candidate):
                return canonical_name
    return None


def is_untracked_heading(line: str) -> bool:
    normalized = line.strip().lstrip("#").strip()
    return normalized.startswith("【") and normalized.endswith("】")


def extract_order_proposals(section_text: str) -> list[ReviewOrderProposal]:
    proposals: list[ReviewOrderProposal] = []
    seen_symbols: set[str] = set()
    for block_proposal in extract_block_order_proposals(section_text):
        proposals.append(block_proposal)
        seen_symbols.add(block_proposal.symbol)

    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        table_proposal = extract_table_order_proposal(line)
        if table_proposal is not None:
            proposals.append(table_proposal)
            seen_symbols.add(table_proposal.symbol)
            continue

        if not line.startswith(("-", "*")):
            continue
        symbol_match = re.search(r"\b([A-Z][A-Z0-9_]{1,})\b", line)
        if not symbol_match:
            continue
        symbol = symbol_match.group(1)
        if symbol in seen_symbols:
            continue
        shares_match = re.search(r"(\d+)\s*(?:株|shares?)", line, flags=re.IGNORECASE)
        if "0段" in line or "見送り" in line:
            recommended_shares = 0
        else:
            recommended_shares = int(shares_match.group(1)) if shares_match else None

        price_match = re.search(
            r"(?:指値|価格|price|@|:)\s*([0-9]+(?:\.[0-9]+)?)\s*(USD|JPY)?",
            line,
            flags=re.IGNORECASE,
        )
        if price_match is None:
            all_numbers = re.findall(r"[0-9]+(?:\.[0-9]+)?", line)
            recommended_price = to_optional_decimal(all_numbers[0]) if all_numbers else None
        else:
            recommended_price = to_optional_decimal(price_match.group(1))

        reason = line
        if "理由" in line:
            reason = line.split("理由", maxsplit=1)[-1].lstrip(" :：")
        proposals.append(
            ReviewOrderProposal(
                symbol=symbol,
                recommended_price=recommended_price,
                recommended_shares=recommended_shares,
                reason=reason.strip(),
            )
        )
    return proposals


def extract_block_order_proposals(section_text: str) -> list[ReviewOrderProposal]:
    proposals: list[ReviewOrderProposal] = []
    current_symbol: str | None = None
    current_lines: list[str] = []

    def flush_current() -> None:
        nonlocal current_symbol, current_lines
        if current_symbol is None:
            return
        proposal = build_block_order_proposal(current_symbol, current_lines)
        if proposal is not None:
            proposals.append(proposal)
        current_symbol = None
        current_lines = []

    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if current_symbol is not None and re.match(r"^SOX(?:投信)?\s*/\s*SMH\s*[:：]", line):
            flush_current()
            continue
        match = re.match(r"^(?P<symbol>[A-Z][A-Z0-9_]{1,})\s*[:：]\s*(?P<body>.*)$", line)
        if match is not None and not line.startswith("|"):
            flush_current()
            current_symbol = match.group("symbol")
            current_lines = [match.group("body").strip()]
            continue
        if current_symbol is not None:
            current_lines.append(line)
    flush_current()
    return proposals


def build_block_order_proposal(symbol: str, lines: list[str]) -> ReviewOrderProposal | None:
    text = normalize_markdown_text(" ".join(line for line in lines if line))
    if not text:
        return None

    price_match = re.search(r"指値\s*([0-9]+(?:\.[0-9]+)?)\s*(?:USD|JPY)?", text, flags=re.IGNORECASE)
    shares_match = re.search(r"株数\s*[:：]?\s*([0-9]+)\s*株", text)
    if shares_match is None:
        shares_match = re.search(r"([0-9]+)\s*株", text)
    if price_match is None and ("見送り" in text or "0段" in text):
        return ReviewOrderProposal(
            symbol=symbol,
            recommended_price=None,
            recommended_shares=0,
            reason=normalize_reason_text(text),
        )
    if price_match is None and shares_match is None:
        return None
    return ReviewOrderProposal(
        symbol=symbol,
        recommended_price=to_optional_decimal(price_match.group(1)) if price_match else None,
        recommended_shares=int(shares_match.group(1)) if shares_match else None,
        reason=normalize_reason_text(text),
    )


def extract_core_spot_buy_plan(
    section_text: str,
    *,
    target_month_start: date | None,
) -> ReviewCoreSpotBuyPlan | None:
    if not section_text.strip():
        return None

    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    allocations = extract_core_spot_buy_allocations(lines)
    schedule = extract_core_spot_buy_schedule(lines, target_month_start=target_month_start)
    total_amount = extract_core_spot_buy_total_amount(lines)
    fixed_amount = extract_labeled_jpy_amount(lines, ("固定core積立額", "固定core積立"))
    spot_amount = extract_labeled_jpy_amount(lines, ("coreスポット買い提案額", "スポット買い提案額"))
    total_deployment = extract_labeled_jpy_amount(
        lines,
        ("固定積立 + スポット買い合計", "固定積立+スポット買い合計", "合計core投入"),
    )
    warnings: list[str] = []

    allocation_total = sum(item.amount_jpy for item in allocations)
    if total_amount is not None and allocation_total and allocation_total != total_amount:
        warnings.append(
            "core spot buy allocation total does not match proposal total: "
            f"{allocation_total} != {total_amount}"
        )

    schedule_total = sum(item.amount_jpy for item in schedule)
    if total_amount is not None and schedule_total and schedule_total != total_amount:
        warnings.append(
            "core spot buy schedule total does not match proposal total: "
            f"{schedule_total} != {total_amount}"
        )

    if any(item.execution_date is None for item in schedule):
        warnings.append("core spot buy schedule includes dates that could not be resolved to a calendar date.")

    return ReviewCoreSpotBuyPlan(
        total_amount_jpy=total_amount,
        account_type=extract_labeled_text(lines, ("account_type", "口座", "account")),
        fixed_core_auto_invest_amount_jpy=fixed_amount,
        spot_buy_amount_jpy=spot_amount,
        total_core_deployment_jpy=total_deployment,
        rule_based_band=extract_labeled_text(lines, ("rule-based band", "rule_based_band")),
        execution_method=extract_labeled_text(lines, ("実行方法",)),
        allocations=allocations,
        schedule=schedule,
        parser_warnings=warnings,
    )


def extract_core_spot_buy_total_amount(lines: list[str]) -> int | None:
    for label in ("coreスポット買い提案額", "提案総額", "スポット買い提案額"):
        amount = extract_labeled_jpy_amount(lines, (label,))
        if amount is not None:
            return amount

    for line in lines:
        if any(skip in line for skip in ("固定core積立", "固定積立", "合計", "配分先", "実行スケジュール")):
            continue
        amount = extract_first_jpy_amount(line)
        if amount is not None:
            return amount
    return None


def extract_core_spot_buy_allocations(lines: list[str]) -> list[CoreSpotBuyAllocation]:
    allocations: list[CoreSpotBuyAllocation] = []
    in_block = False
    for line in lines:
        if "配分先内訳" in line:
            in_block = True
            continue
        if in_block and any(marker in line for marker in ("配分理由", "実行方法", "実行スケジュール", "判断根拠")):
            break
        if not in_block:
            continue

        allocation = extract_allocation_line(line)
        if allocation is not None:
            allocations.append(allocation)
    return allocations


def extract_allocation_line(line: str) -> CoreSpotBuyAllocation | None:
    if "合計" in line:
        return None
    if line.startswith("|") and line.endswith("|"):
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 2 and not is_markdown_separator_row(cells):
            amount = extract_first_jpy_amount(cells[-1]) or parse_jpy_digits(cells[-1])
            if amount is not None and "fund" not in cells[0].lower():
                return CoreSpotBuyAllocation(fund_name=normalize_markdown_text(cells[0]), amount_jpy=amount)
        return None

    match = re.match(
        r"^(?:[-*]\s*)?(?P<fund>.+?)[:：]\s*(?:\*\*)?(?P<amount>[0-9][0-9,]*)\s*円",
        line,
    )
    if match is None:
        return None
    return CoreSpotBuyAllocation(
        fund_name=normalize_markdown_text(match.group("fund")),
        amount_jpy=parse_jpy_digits(match.group("amount")),
    )


def extract_core_spot_buy_schedule(
    lines: list[str],
    *,
    target_month_start: date | None,
) -> list[CoreSpotBuyScheduleItem]:
    schedule: list[CoreSpotBuyScheduleItem] = []
    in_block = False
    for line in lines:
        if "実行スケジュールなし" in line:
            return []
        if "実行スケジュール" in line:
            in_block = True
            continue
        if in_block and any(marker in line for marker in ("判断根拠", "相場面", "ポートフォリオ歪み", "流動性水準")):
            break
        if not in_block:
            continue

        item = extract_schedule_table_line(line, target_month_start=target_month_start)
        if item is None:
            item = extract_schedule_bullet_line(line, target_month_start=target_month_start)
        if item is not None:
            schedule.append(item)
    return schedule


def extract_schedule_table_line(
    line: str,
    *,
    target_month_start: date | None,
) -> CoreSpotBuyScheduleItem | None:
    if not (line.startswith("|") and line.endswith("|")):
        return None
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if len(cells) < 3 or is_markdown_separator_row(cells):
        return None
    execution_date = parse_schedule_date(cells[0], target_month_start=target_month_start)
    if execution_date is None and not looks_like_schedule_date(cells[0]):
        return None
    amount = extract_first_jpy_amount(cells[2]) or parse_jpy_digits(cells[2])
    if amount is None:
        return None
    return CoreSpotBuyScheduleItem(
        execution_date=execution_date,
        fund_name=normalize_markdown_text(cells[1]),
        amount_jpy=amount,
        raw_text=line,
    )


def extract_schedule_bullet_line(
    line: str,
    *,
    target_month_start: date | None,
) -> CoreSpotBuyScheduleItem | None:
    match = re.match(
        r"^(?:[-*]\s*)?(?P<date>(?:20[0-9]{2}[-/][0-9]{1,2}[-/][0-9]{1,2}|(?:20[0-9]{2}年)?[0-9]{1,2}月[0-9]{1,2}日))\s*[:：]\s*(?P<body>.+)$",
        line,
    )
    if match is None:
        return None
    amount_matches = list(re.finditer(r"([0-9][0-9,]*)\s*円", match.group("body")))
    if not amount_matches:
        return None
    amount_match = amount_matches[-1]
    fund_name = match.group("body")[: amount_match.start()].strip()
    return CoreSpotBuyScheduleItem(
        execution_date=parse_schedule_date(match.group("date"), target_month_start=target_month_start),
        fund_name=normalize_markdown_text(fund_name),
        amount_jpy=parse_jpy_digits(amount_match.group(1)),
        raw_text=line,
    )


def extract_labeled_jpy_amount(lines: list[str], labels: tuple[str, ...]) -> int | None:
    for line in lines:
        normalized = normalize_markdown_text(line)
        for label in labels:
            if label not in normalized:
                continue
            amount = extract_first_jpy_amount(normalized)
            if amount is not None:
                return amount
    return None


def extract_labeled_text(lines: list[str], labels: tuple[str, ...]) -> str | None:
    for line in lines:
        normalized = normalize_markdown_text(line)
        for label in labels:
            match = re.match(rf"^(?:[-*]\s*)?{re.escape(label)}\s*[:：]\s*(?P<value>.+)$", normalized)
            if match is not None:
                value = match.group("value").strip()
                return value or None
    return None


def extract_first_jpy_amount(value: str) -> int | None:
    match = re.search(r"([0-9][0-9,]*)\s*円", value)
    if match is None:
        return None
    return parse_jpy_digits(match.group(1))


def parse_jpy_digits(value: str) -> int | None:
    normalized = normalize_markdown_text(value).replace(",", "").strip()
    if not normalized.isdigit():
        return None
    return int(normalized)


def parse_schedule_date(value: str, *, target_month_start: date | None) -> date | None:
    normalized = normalize_markdown_text(value)
    iso_match = re.match(r"^(20[0-9]{2})[-/]([0-9]{1,2})[-/]([0-9]{1,2})$", normalized)
    if iso_match is not None:
        return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))

    japanese_match = re.match(r"^(?:(20[0-9]{2})年)?([0-9]{1,2})月([0-9]{1,2})日$", normalized)
    if japanese_match is None:
        return None
    year_text = japanese_match.group(1)
    if year_text is None and target_month_start is None:
        return None
    year = int(year_text) if year_text is not None else target_month_start.year
    return date(year, int(japanese_match.group(2)), int(japanese_match.group(3)))


def looks_like_schedule_date(value: str) -> bool:
    normalized = normalize_markdown_text(value)
    return bool(
        re.match(r"^(20[0-9]{2})[-/]([0-9]{1,2})[-/]([0-9]{1,2})$", normalized)
        or re.match(r"^(?:(20[0-9]{2})年)?([0-9]{1,2})月([0-9]{1,2})日$", normalized)
    )


def parse_review_target_month(value: str | None) -> date | None:
    if value is None:
        return None
    match = re.search(r"(20[0-9]{2})[_/-]([0-9]{1,2})", str(value))
    if match is None:
        return None
    return date(int(match.group(1)), int(match.group(2)), 1)


def infer_review_target_month_from_text(review_text: str) -> date | None:
    for pattern in (
        r"review_target_month\s*[:：]\s*(20[0-9]{2})[_/-]([0-9]{1,2})",
        r"対象月\s*[:：]\s*(20[0-9]{2})[_/-]([0-9]{1,2})",
        r"(20[0-9]{2})[_/-]([0-9]{1,2})\s*月次レビュー",
        r"(20[0-9]{2})[_/-]([0-9]{1,2})",
    ):
        match = re.search(pattern, review_text)
        if match is not None:
            return date(int(match.group(1)), int(match.group(2)), 1)
    return None


def is_markdown_separator_row(cells: list[str]) -> bool:
    return all(set(cell.replace(":", "").strip()) <= {"-"} for cell in cells if cell.strip())


def normalize_markdown_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("**", "").replace("`", "")).strip()


def extract_table_order_proposal(line: str) -> ReviewOrderProposal | None:
    if not line.startswith("|") or not line.endswith("|"):
        return None
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if len(cells) < 2:
        return None
    first_cell = cells[0]
    if not first_cell or set(first_cell) <= {"-"} or "銘柄" in first_cell:
        return None
    symbol_match = re.search(r"\b([A-Z][A-Z0-9_]{1,})\b", first_cell)
    if not symbol_match:
        return None
    symbol = symbol_match.group(1)
    proposal_text = cells[1]
    reason = cells[2] if len(cells) >= 3 else line
    if "見送り" in proposal_text or "0段" in proposal_text:
        return ReviewOrderProposal(
            symbol=symbol,
            recommended_price=None,
            recommended_shares=0,
            reason=normalize_reason_text(reason or proposal_text),
        )
    price_match = re.search(r"(?:指値|価格|price|@|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:USD|JPY)?", proposal_text)
    shares_match = re.search(r"(\d+)\s*(?:株|shares?)", proposal_text, flags=re.IGNORECASE)
    return ReviewOrderProposal(
        symbol=symbol,
        recommended_price=to_optional_decimal(price_match.group(1)) if price_match else None,
        recommended_shares=int(shares_match.group(1)) if shares_match else None,
        reason=normalize_reason_text(reason or proposal_text),
    )


def normalize_reason_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_sox_decision(section_text: str) -> str | None:
    normalized = section_text.replace(" ", "")
    if "買わない" in normalized or "見送り" in normalized:
        return "買わない"
    if "買う" in normalized:
        return "買う"
    return None


def extract_priority_lists(section_text: str) -> tuple[list[str], list[str], list[str]]:
    buckets = {"must": [], "should": [], "nice_to_have": []}
    current_bucket: str | None = None
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower().replace(" ", "")
        for bucket in buckets:
            if lowered.startswith(bucket):
                current_bucket = bucket
                remainder = re.split(r"[:：]", line, maxsplit=1)
                if len(remainder) > 1 and remainder[1].strip():
                    buckets[bucket].append(remainder[1].strip().lstrip("- ").strip())
                break
        else:
            if current_bucket is not None and line.startswith(("-", "*")):
                buckets[current_bucket].append(line.lstrip("-* ").strip())
    return buckets["must"], buckets["should"], buckets["nice_to_have"]


def extract_bullets(section_text: str) -> list[str]:
    bullets: list[str] = []
    for raw_line in section_text.splitlines():
        line = raw_line.strip()
        if line.startswith(("-", "*")):
            bullets.append(line.lstrip("-* ").strip())
    return bullets
