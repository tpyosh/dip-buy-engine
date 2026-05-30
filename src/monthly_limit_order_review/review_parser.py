from __future__ import annotations

import re
from decimal import Decimal

from .models import ReviewFeedback, ReviewOrderProposal
from .utils import to_optional_decimal

SECTION_HEADINGS = {
    "monthly_proposals": ["今月の指値提案", "指値提案"],
    "sox_decision": ["SOX投信判定", "SOX判定"],
    "portfolio_diagnosis": ["ポートフォリオ診断", "資産配分診断"],
    "rule_review": ["四半期ルール見直し", "ルール改善レビュー", "改善レビュー"],
    "codex_summary": ["Codex向け修正要約", "Codex 向け修正要約", "修正要約"],
}


def parse_review_feedback(review_text: str) -> ReviewFeedback:
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
