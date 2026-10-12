"""Synthetic cases only. Run with unittest discover; no private files or network."""

import copy
import json
import subprocess
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

from tax_math import aggregate, offset, estimate, money


def sale(rid="S1", **changes):
    row = {"id": rid, "economic_id": rid, "account_id": "ACCOUNT_A",
           "account_type": "specified_withholding", "tax_group": "listed", "kind": "sale",
           "year": 2026, "proceeds_jpy": "100000", "acquisition_cost_jpy": "80000",
           "selling_cost_jpy": "100", "status": "verified", "evidence_refs": ["SYNTHETIC:trade:1"]}
    row.update(changes)
    return row


def ledger(*rows, complete=True):
    return {"year": 2026, "scope_complete": complete, "records": list(rows)}


def account(aid="ACCOUNT_A", **changes):
    row = {"account_id": aid, "account_type": "specified_withholding", "tax_group": "listed",
           "all_losses_eligible": True, "net_sales_jpy": "100000", "eligible_distributions_jpy": "20000",
           "declare_sales": True, "declare_distributions": True, "distribution_method": "separate",
           "status": "verified", "evidence_refs": ["SYNTHETIC:annual:1"]}
    row.update(changes)
    return row


def claim(origin=2023, amount="60000", **changes):
    row = {"id": "LOSS_" + str(origin), "loss_year": origin, "expiry_year": origin + 3,
           "remaining_jpy": amount, "filing_verified": True, "status": "verified",
           "evidence_refs": ["SYNTHETIC:returns:continuity"]}
    row.update(changes)
    return row


def scenario(accounts=None, claims=None):
    return {"year": 2026, "scope_complete": True,
            "rules": {"year": 2026, "verified": True, "loss_order": "oldest_first",
                      "income_order": "sales_then_distributions", "evidence_refs": ["SYNTHETIC:rule"]},
            "accounts": accounts if accounts is not None else [account()],
            "carryovers": claims if claims is not None else []}


def estimate_input(target=2026):
    def part(cid, base, rate, jurisdiction="national"):
        return {"id": cid, "base": base, "rate": rate, "jurisdiction": jurisdiction,
                "rounding": "none", "rounding_quantum_jpy": "0", "rule_refs": ["SYNTHETIC:rate"]}
    parts = [part("income_tax", "income", "0.15"),
             part("reconstruction", "income_tax", "0.021" if target == 2026 else "0.011")]
    if target == 2027:
        parts.append(part("defense", "income_tax", "0.01"))
    parts.append(part("resident", "income", "0.05", "resident"))
    return {"year": target, "mode": "conditional_marginal_estimate", "status": "verified",
            "evidence_refs": ["SYNTHETIC:base"], "taxable_income_jpy": "100000", "components": parts}


class ArithmeticTests(unittest.TestCase):
    def test_profit_loss_and_fees(self):
        out = aggregate(ledger(sale(), sale("S2", proceeds_jpy="50000")))["groups"][0]
        self.assertEqual(out["gross_gains_jpy"], D("19900"))
        self.assertEqual(out["gross_losses_jpy"], D("30100"))
        self.assertEqual(out["total_jpy"], D("-10200"))

    def test_unknown_cost_is_not_zero(self):
        out = aggregate(ledger(sale(), sale("S2", acquisition_cost_jpy=None)))["groups"][0]
        self.assertIsNone(out["total_jpy"])
        self.assertIsNone(out["gross_gains_jpy"])
        self.assertEqual(out["known_subtotal_jpy"], D("19900"))
        self.assertEqual(out["unresolved_ids"], ["S2"])

    def test_unknown_fee_is_not_zero(self):
        out = aggregate(ledger(sale(selling_cost_jpy=None)))["groups"][0]
        self.assertIsNone(out["total_jpy"])

    def test_unverified_numeric_value_is_not_confirmed(self):
        out = aggregate(ledger(sale(status="unverified", evidence_refs=[])))["groups"][0]
        self.assertEqual(out["status"], "unverified")
        self.assertIsNone(out["total_jpy"])

    def test_incomplete_period_is_not_an_annual_total(self):
        out = aggregate(ledger(sale(), complete=False))["groups"][0]
        self.assertIsNone(out["total_jpy"])
        self.assertEqual(out["status"], "provisional")

    def test_provisional_remains_provisional(self):
        self.assertEqual(aggregate(ledger(sale(status="provisional")))["groups"][0]["status"], "provisional")

    def test_not_applicable_remains_not_applicable(self):
        out = aggregate(ledger(sale(status="not_applicable", proceeds_jpy=None,
                                    acquisition_cost_jpy=None, selling_cost_jpy=None, evidence_refs=[])))["groups"][0]
        self.assertEqual(out["status"], "not_applicable")
        self.assertIsNone(out["total_jpy"])

    def test_nisa_general_and_listed_are_separate(self):
        rows = [sale(), sale("S2", account_id="ACCOUNT_N", account_type="nisa", tax_group="nisa"),
                sale("S3", account_id="ACCOUNT_G", account_type="general", tax_group="general")]
        self.assertEqual({g["tax_group"] for g in aggregate(ledger(*rows))["groups"]}, {"listed", "nisa", "general"})

    def test_unrealized_and_capital_returns_not_sales(self):
        rows = [sale(), sale("U1", kind="unrealized", amount_jpy="-25000"),
                sale("R1", kind="return_capital", amount_jpy="1000")]
        out = {g["kind"]: g for g in aggregate(ledger(*rows))["groups"]}
        self.assertEqual(out["sale"]["total_jpy"], D("19900"))
        self.assertEqual(out["unrealized"]["total_jpy"], D("-25000"))
        self.assertIsNone(out["return_capital"]["gross_gains_jpy"])

    def test_duplicate_record_or_economic_id_rejected(self):
        for second in [sale(), sale("S2", economic_id="S1")]:
            with self.subTest(second=second["id"]), self.assertRaises(ValueError):
                aggregate(ledger(sale(), second))

    def test_tax_year_not_inferred_from_trade_date(self):
        with self.assertRaises(ValueError):
            aggregate(ledger(sale(year=2027)))

    def test_account_classification_conflicts_rejected(self):
        with self.assertRaises(ValueError):
            aggregate(ledger(sale(account_type="nisa")))
        with self.assertRaises(ValueError):
            aggregate(ledger(sale(), sale("S2", account_type="general")))

    def test_no_source_no_verified_result(self):
        with self.assertRaises(ValueError):
            aggregate(ledger(sale(evidence_refs=[])))

    def test_decimal_money_validation(self):
        for bad in [0.1, None, True, "NaN", "Infinity", "1e3", "1,000", "-1"]:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                money(bad, "test", nonnegative=True)
        self.assertEqual(money("0.1", "test") + money("0.2", "test"), D("0.3"))

    def test_cross_account_loss_and_dividend_offset(self):
        out = offset(scenario([account(), account("ACCOUNT_B", net_sales_jpy="-150000", eligible_distributions_jpy="10000")]))
        self.assertEqual(out["current_loss_to_distributions_jpy"], D("30000"))
        self.assertEqual(out["new_loss_potential_carryover_jpy"], D("20000"))
        self.assertEqual(out["taxable_sales_before_other_deductions_jpy"], 0)
        self.assertEqual(out["taxable_distributions_before_other_deductions_jpy"], 0)

    def test_loss_without_profit_has_no_immediate_tax_saving(self):
        out = offset(scenario([account(net_sales_jpy="-100000", eligible_distributions_jpy="0")]))
        self.assertEqual(out["current_loss_to_distributions_jpy"], 0)
        self.assertEqual(out["new_loss_potential_carryover_jpy"], D("100000"))

    def test_withholding_loss_requires_received_distributions(self):
        with self.assertRaisesRegex(ValueError, "same-account"):
            offset(scenario([account(net_sales_jpy="-10000", declare_distributions=False)]))

    def test_gain_only_declaration_allowed(self):
        out = offset(scenario([account(declare_distributions=False)]))
        self.assertEqual(out["distributions_before_offsets_jpy"], 0)

    def test_dividends_only_declaration_allowed(self):
        out = offset(scenario([account(declare_sales=False)]))
        self.assertEqual(out["net_sales_before_offsets_jpy"], 0)
        self.assertEqual(out["taxable_distributions_before_other_deductions_jpy"], D("20000"))

    def test_ineligible_tax_groups_and_accounts_rejected(self):
        for row in [account(account_type="nisa"), account(account_type="ideco"),
                    account(tax_group="general"), account(all_losses_eligible=False)]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                offset(scenario([row]))

    def test_aggregate_dividend_taxation_rejected(self):
        with self.assertRaises(ValueError):
            offset(scenario([account(distribution_method="aggregate")]))

    def test_unknown_input_blocks_dependent_calculation(self):
        with self.assertRaises(ValueError):
            offset(scenario([account(net_sales_jpy=None)]))
        with self.assertRaises(ValueError):
            offset(scenario([account(status="unverified")]))

    def test_provisional_current_year_is_allowed(self):
        self.assertEqual(offset(scenario([account(status="provisional")]))["status"], "provisional")

    def test_unverified_carryover_not_used(self):
        for c in [claim(status="provisional"), claim(filing_verified=False), claim(evidence_refs=[])]:
            with self.subTest(claim=c), self.assertRaises(ValueError):
                offset(scenario(claims=[c]))

    def test_oldest_loss_first_and_sales_before_distributions(self):
        out = offset(scenario(claims=[claim(2025, "80000"), claim(2023, "60000")]))
        old, new = out["carryovers"]
        self.assertEqual(old["loss_year"], 2023)
        self.assertEqual(old["used_sales_jpy"], D("60000"))
        self.assertEqual(new["used_sales_jpy"], D("40000"))
        self.assertEqual(new["used_distributions_jpy"], D("20000"))
        self.assertEqual(new["available_next_year_jpy"], D("20000"))

    def test_expiry_year_is_usable_but_unused_expires(self):
        out = offset(scenario(claims=[claim(2023, "150000")]))["carryovers"][0]
        self.assertEqual(out["used_sales_jpy"] + out["used_distributions_jpy"], D("120000"))
        self.assertEqual(out["expired_by_year_end_jpy"], D("30000"))
        self.assertEqual(out["available_next_year_jpy"], 0)

    def test_expired_loss_not_applied(self):
        out = offset(scenario(claims=[claim(2022, "50000")]))
        self.assertEqual(out["carryovers"][0]["used_sales_jpy"], 0)
        self.assertEqual(out["carryovers"][0]["expired_by_year_end_jpy"], D("50000"))
        self.assertEqual(out["taxable_sales_before_other_deductions_jpy"], D("100000"))

    def test_same_year_or_wrong_expiry_claim_rejected(self):
        for c in [claim(2026), claim(expiry_year=2027)]:
            with self.subTest(claim=c), self.assertRaises(ValueError):
                offset(scenario(claims=[c]))

    def test_missing_annual_rules_and_partial_scope_rejected(self):
        for path, value in [("verified", False), ("year", 2025), ("loss_order", "newest_first")]:
            data = scenario()
            data["rules"][path] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                offset(data)
        data = scenario(); data["scope_complete"] = False
        with self.assertRaises(ValueError):
            offset(data)

    def test_input_not_mutated(self):
        data = scenario(claims=[claim()]); before = copy.deepcopy(data)
        offset(data)
        self.assertEqual(data, before)

    def test_2026_2027_equal_total_different_components(self):
        before, after = estimate(estimate_input()), estimate(estimate_input(2027))
        self.assertEqual(before["totals_jpy"], {"national": D("15315"), "resident": D("5000")})
        self.assertEqual(before["totals_jpy"], after["totals_jpy"])
        self.assertNotIn("defense", [c["id"] for c in before["components"]])
        self.assertIn("defense", [c["id"] for c in after["components"]])
        self.assertFalse(after["is_final_tax"])
        self.assertEqual(after["status"], "provisional")

    def test_explicit_rounding_and_no_rounding_are_distinct(self):
        data = estimate_input(); data["taxable_income_jpy"] = "10001"
        raw = estimate(data)["components"][0]["estimate_jpy"]
        data["components"][0].update(rounding="floor", rounding_quantum_jpy="1")
        rounded = estimate(data)["components"][0]["estimate_jpy"]
        self.assertEqual(raw, D("1500.15")); self.assertEqual(rounded, D("1500"))

    def test_unsupported_final_tax_request_rejected(self):
        data = estimate_input(); data["mode"] = "final_return"
        with self.assertRaises(ValueError):
            estimate(data)

    def test_cli_stdout_and_invalid_json(self):
        script = str(Path(__file__).with_name("tax_math.py"))
        result = subprocess.run([sys.executable, script, "aggregate", "-"],
                                input=json.dumps(ledger(sale())), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["groups"][0]["total_jpy"], "19900")
        result = subprocess.run([sys.executable, script, "aggregate", "-"],
                                input='{"year":2026,"year":2025}', text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(result.stdout)
        self.assertIn("duplicate JSON key", json.loads(result.stderr)["error"])

    def test_cli_rejects_non_finite_json_even_in_unused_field(self):
        script = str(Path(__file__).with_name("tax_math.py"))
        raw = json.dumps(ledger(sale()))[:-1] + ',"unused":NaN}'
        result = subprocess.run([sys.executable, script, "aggregate", "-"],
                                input=raw, text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("non-finite", json.loads(result.stderr)["error"])


if __name__ == "__main__":
    unittest.main()
