#!/usr/bin/env python3
"""Stateless, offline arithmetic; legal eligibility must be checked by the caller."""

import argparse
import json
import re
import sys
from decimal import Decimal, localcontext, ROUND_DOWN
from pathlib import Path

ZERO = Decimal(0)
STATES = {"verified", "provisional", "unverified", "not_applicable"}
ACCOUNT_TYPES = {"specified_withholding", "specified_no_withholding", "general", "nisa", "ideco"}
GROUPS = {"listed", "general", "nisa", "ideco", "other"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def money(value, path, nonnegative=False):
    require(isinstance(value, str) and re.fullmatch(r"-?\d{1,24}(?:\.\d{1,12})?", value),
            f"{path}: decimal string required (no float, exponent, comma or unknown)")
    result = Decimal(value)
    require(not nonnegative or result >= 0, f"{path}: negative amount")
    return result


def refs(value, path):
    require(isinstance(value, list) and value and all(isinstance(x, str) and x.strip() for x in value),
            f"{path}: nonempty evidence/rule references required")


def evidence(row, path, usable=False):
    require(isinstance(row, dict), f"{path}: object required")
    status = row.get("status")
    require(status in STATES, f"{path}: invalid status")
    if "evidence_refs" in row:
        require(isinstance(row["evidence_refs"], list) and
                all(isinstance(x, str) and x.strip() for x in row["evidence_refs"]),
                f"{path}: evidence_refs must be a list of nonempty strings")
    if status in {"verified", "provisional"}:
        refs(row.get("evidence_refs"), path)
    if usable:
        require(status in {"verified", "provisional"}, f"{path}: unresolved input")
    return status


def year(value):
    require(type(value) is int and 1900 <= value <= 9999, "year: invalid integer")
    return value


def unique(rows, key):
    seen = set()
    for row in rows:
        require(isinstance(row, dict), f"{key}: object required")
        value = row.get(key)
        require(isinstance(value, str) and value.strip(), f"{key}: nonempty ID required")
        require(value not in seen, f"duplicate {key}: {value}")
        seen.add(value)


def aggregate(data):
    target = year(data["year"])
    require(type(data["scope_complete"]) is bool, "scope_complete: boolean required")
    records = data["records"]
    require(isinstance(records, list), "records: list required")
    unique(records, "id")
    unique(records, "economic_id")
    groups, account_types = {}, {}
    for row in records:
        rid = row["id"]
        require(year(row["year"]) == target, f"{rid}: tax year mismatch")
        aid, atype, group, kind = (row[k] for k in ("account_id", "account_type", "tax_group", "kind"))
        require(isinstance(aid, str) and aid.strip(), f"{rid}: account ID required")
        require(atype in ACCOUNT_TYPES and group in GROUPS, f"{rid}: unknown account/tax group")
        require(account_types.setdefault(aid, atype) == atype, f"{rid}: account type conflict")
        for special in ("nisa", "ideco"):
            require((atype == special) == (group == special), f"{rid}: {special} classification conflict")
        require(kind in {"sale", "dividend", "return_capital", "unrealized"}, f"{rid}: unknown kind")
        status = evidence(row, rid)
        key = (aid, atype, group, kind)
        bucket = groups.setdefault(key, {"values": [], "unresolved_ids": [], "record_ids": [],
                                         "evidence_refs": [], "statuses": []})
        bucket["record_ids"].append(rid)
        bucket["statuses"].append(status)
        bucket["evidence_refs"].extend(row.get("evidence_refs", []))
        fields = ("proceeds_jpy", "acquisition_cost_jpy", "selling_cost_jpy") if kind == "sale" else ("amount_jpy",)
        values = [None if row.get(k) is None else money(row[k], f"{rid}.{k}", kind != "unrealized") for k in fields]
        if status not in {"verified", "provisional"} or any(v is None for v in values):
            bucket["unresolved_ids"].append(rid)
            continue
        amount = values[0] - values[1] - values[2] if kind == "sale" else values[0]
        bucket["values"].append(amount)
    output = []
    for key, bucket in sorted(groups.items()):
        aid, atype, group, kind = key
        known = sum(bucket["values"], ZERO)
        complete = not bucket["unresolved_ids"] and data["scope_complete"]
        status = "not_applicable" if set(bucket["statuses"]) == {"not_applicable"} else "unverified" if bucket["unresolved_ids"] else (
            "provisional" if not complete or "provisional" in bucket["statuses"] else "verified")
        output.append({"account_id": aid, "account_type": atype, "tax_group": group, "kind": kind,
                       "status": status, "total_jpy": known if complete else None,
                       "known_subtotal_jpy": known,
                       "gross_gains_jpy": sum((v for v in bucket["values"] if v > 0), ZERO) if complete and kind == "sale" else None,
                       "gross_losses_jpy": -sum((v for v in bucket["values"] if v < 0), ZERO) if complete and kind == "sale" else None,
                       "unresolved_ids": bucket["unresolved_ids"], "record_ids": bucket["record_ids"],
                       "evidence_refs": sorted(set(bucket["evidence_refs"]))})
    return {"year": target, "scope_complete": data["scope_complete"], "groups": output,
            "note": "Separate groups; no automatic tax netting. Match annual statements outside this helper."}


def offset(data):
    target = year(data["year"])
    rule = data["rules"]
    require(rule["verified"] is True and year(rule["year"]) == target, "rules: verify target-year rules first")
    require(rule["loss_order"] == "oldest_first" and rule["income_order"] == "sales_then_distributions",
            "rules: unsupported order; use official forms instead")
    refs(rule["evidence_refs"], "rules")
    require(data["scope_complete"] is True, "offset: incomplete selected scenario scope")
    accounts = data["accounts"]
    require(isinstance(accounts, list) and accounts, "accounts: nonempty selected scenario required")
    unique(accounts, "account_id")
    sales, dividends, statuses = ZERO, ZERO, []
    selected = []
    for row in accounts:
        aid = row["account_id"]
        statuses.append(evidence(row, aid, usable=True))
        require(row["account_type"] in ACCOUNT_TYPES - {"nisa", "ideco"}, f"{aid}: taxable account required")
        require(row["tax_group"] == "listed" and row["all_losses_eligible"] is True,
                f"{aid}: only vetted listed eligible-loss scenarios supported")
        net = money(row["net_sales_jpy"], aid + ".net_sales_jpy")
        div = money(row["eligible_distributions_jpy"], aid + ".eligible_distributions_jpy", True)
        s, d = row["declare_sales"], row["declare_distributions"]
        require(type(s) is bool and type(d) is bool, f"{aid}: selection booleans required")
        require(s or d, f"{aid}: omit unselected accounts from this calculation")
        require(not d or row["distribution_method"] == "separate", f"{aid}: distributions must use separate taxation")
        require(not (s and net < 0 and div > 0 and row["account_type"] == "specified_withholding") or d,
                f"{aid}: withholding loss declaration requires same-account distributions")
        if s:
            sales += net
        if d:
            dividends += div
        selected.append({"account_id": aid, "declared_sales_jpy": net if s else ZERO,
                         "declared_distributions_jpy": div if d else ZERO,
                         "evidence_refs": row["evidence_refs"]})
    current_offset = min(max(-sales, ZERO), dividends)
    sales_base = max(sales, ZERO)
    dividends_base = dividends - current_offset
    new_loss = max(-sales - current_offset, ZERO)
    claims = data["carryovers"]
    require(isinstance(claims, list), "carryovers: list required")
    unique(claims, "id")
    require(len({c["loss_year"] for c in claims}) == len(claims), "combine carryovers by loss year first")
    applied = []
    for claim in sorted(claims, key=lambda c: c["loss_year"]):
        cid = claim["id"]
        require(evidence(claim, cid, usable=True) == "verified" and claim["filing_verified"] is True,
                f"{cid}: carryover requires verified return/continuity evidence")
        origin = year(claim["loss_year"])
        require(origin < target and year(claim["expiry_year"]) == origin + 3, f"{cid}: invalid loss/expiry year")
        balance = money(claim["remaining_jpy"], cid + ".remaining_jpy", True)
        used_sales = used_div = ZERO
        if target <= origin + 3:
            used_sales = min(balance, sales_base)
            sales_base -= used_sales
            used_div = min(balance - used_sales, dividends_base)
            dividends_base -= used_div
        remaining = balance - used_sales - used_div
        expired = remaining if target >= origin + 3 else ZERO
        applied.append({"id": cid, "loss_year": origin, "expiry_year": origin + 3,
                        "opening_jpy": balance, "used_sales_jpy": used_sales, "used_distributions_jpy": used_div,
                        "unused_before_expiry_jpy": remaining, "expired_by_year_end_jpy": expired,
                        "available_next_year_jpy": remaining - expired, "evidence_refs": claim["evidence_refs"]})
    return {"year": target, "status": "provisional" if "provisional" in statuses else "verified",
            "selected_accounts": selected, "net_sales_before_offsets_jpy": sales,
            "distributions_before_offsets_jpy": dividends, "current_loss_to_distributions_jpy": current_offset,
            "taxable_sales_before_other_deductions_jpy": sales_base,
            "taxable_distributions_before_other_deductions_jpy": dividends_base,
            "new_loss_potential_carryover_jpy": new_loss, "new_loss_expiry_year": target + 3,
            "carryovers": applied, "rule_refs": rule["evidence_refs"],
            "note": "New carryover depends on required filing; no withholding refund or final liability calculated."}


def estimate(data):
    target = year(data["year"])
    require(data["mode"] == "conditional_marginal_estimate", "estimate: not a final return calculation")
    evidence(data, "estimate", usable=True)
    taxable = money(data["taxable_income_jpy"], "taxable_income_jpy", True)
    components = data["components"]
    require(isinstance(components, list) and components, "components: nonempty list required")
    unique(components, "id")
    out, computed, totals = [], {}, {"national": ZERO, "resident": ZERO}
    for c in components:
        refs(c["rule_refs"], c["id"])
        require(c["jurisdiction"] in totals, "unknown jurisdiction")
        rate = money(c["rate"], c["id"] + ".rate", True)
        require(rate <= 1, "rate must be a fraction <= 1")
        base = c["base"]
        require(base == "income" or base in computed, "component base must be income or an earlier component")
        quantum = money(c["rounding_quantum_jpy"], c["id"] + ".rounding_quantum_jpy", True)
        require(c["rounding"] in {"none", "floor"}, "unsupported rounding")
        require((c["rounding"] == "none" and quantum == 0) or (c["rounding"] == "floor" and quantum > 0),
                "rounding quantum mismatch")
        raw = (taxable if base == "income" else computed[base]) * rate
        value = raw if c["rounding"] == "none" else (raw / quantum).to_integral_value(rounding=ROUND_DOWN) * quantum
        computed[c["id"]] = value
        totals[c["jurisdiction"]] += value
        out.append({**c, "unrounded_jpy": raw, "estimate_jpy": value})
    return {"year": target, "status": "provisional", "is_final_tax": False,
            "input_status": data["status"], "evidence_refs": data["evidence_refs"],
            "taxable_income_jpy": taxable, "components": out, "totals_jpy": totals,
            "note": "Conditional arithmetic only: no deductions, credits, high-income adjustment, withholding or refund."}


def serialize(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    raise TypeError(type(value).__name__)


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"non-finite JSON constant: {value}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["aggregate", "offset", "estimate"])
    parser.add_argument("input", help="Explicit input JSON path, or - for stdin; outputs JSON to stdout only")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        data = json.loads(raw, object_pairs_hook=no_duplicate_keys, parse_constant=reject_constant)
        with localcontext() as ctx:
            ctx.prec = 80
            result = {"aggregate": aggregate, "offset": offset, "estimate": estimate}[args.operation](data)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=serialize, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError, ArithmeticError) as error:
        print(json.dumps({"error": str(error), "status": "unverified"}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
