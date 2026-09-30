from __future__ import annotations

import unittest
import tempfile
from decimal import Decimal
from pathlib import Path

from bookkeeping_workflow.classify import RuleBasedClassifier
from bookkeeping_workflow.models import TransactionType
from bookkeeping_workflow.normalize import load_transactions
from bookkeeping_workflow.workflow import EXAMPLES, run_workflow


class SyntheticWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = run_workflow()
        cls.entries = {entry.transaction.transaction_id: entry for entry in cls.result.entries}

    def test_transaction_normalization_preserves_facts(self) -> None:
        rows = load_transactions(EXAMPLES / "synthetic_transactions.csv")
        expense = next(row for row in rows if row.transaction_id == "tx-owner-expense")
        self.assertEqual(expense.date, "2026-06-10")
        self.assertEqual(expense.amount, Decimal("86.50"))
        self.assertEqual(expense.payment_source.value, "Owner Personal")

    def test_missing_payment_source_and_direction_are_not_invented(self) -> None:
        header = "transaction_id,date,counterparty,amount,direction,description,payment_source,document_type,document_ref,document_status,business_use,business_use_percent,linked_transaction_id,invoice_id,financing_source,mileage_miles\n"
        row = "tx-incomplete,2026-06-28,Unknown Vendor,12.00,,Unclear purchase,,receipt,,Missing,unclear,,,,,\n"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.csv"
            path.write_text(header + row, encoding="utf-8")
            transaction = load_transactions(path)[0]
        self.assertIsNone(transaction.direction)
        self.assertIsNone(transaction.payment_source)
        classification = RuleBasedClassifier().classify(transaction)
        self.assertTrue(classification.review_required)
        self.assertIn("transaction direction is missing", classification.review_reasons)
        self.assertIn("payment source is missing", classification.review_reasons)

    def test_rule_based_category_assignment(self) -> None:
        entry = self.entries["tx-software"]
        self.assertEqual(entry.classification.transaction_type, TransactionType.ORDINARY_EXPENSE)
        self.assertEqual(entry.classification.category, "Software")
        self.assertIn("outflow", entry.classification.rule)

    def test_owner_paid_expense_is_counted_once_after_reimbursement(self) -> None:
        original = self.entries["tx-owner-expense"]
        reimbursement = self.entries["tx-owner-reimbursement"]
        self.assertEqual(original.classification.transaction_type, TransactionType.ORDINARY_EXPENSE)
        self.assertEqual(original.transaction.payment_source.value, "Owner Personal")
        self.assertEqual(reimbursement.classification.transaction_type, TransactionType.REIMBURSEMENT)
        self.assertEqual(reimbursement.transaction.linked_transaction_id, "tx-owner-expense")
        self.assertEqual(self.result.summary.operating_expenses, Decimal("592.50"))

    def test_owner_paid_expense_without_reimbursement_is_flagged(self) -> None:
        self.assertEqual(self.result.reconciliation.owner_reimbursements_awaiting, ("tx-owner-pending",))

    def test_financed_asset_is_recorded_once_and_payment_is_not_asset(self) -> None:
        self.assertEqual(len(self.result.assets), 1)
        asset = self.result.assets[0]
        self.assertEqual(asset.transaction_id, "tx-asset")
        self.assertEqual(asset.purchase_cost, Decimal("2000.00"))
        self.assertEqual(asset.purchase_date, "2026-06-12")
        self.assertEqual(asset.financing_source, "Northstar Fictional Finance")
        finance_payment = self.entries["tx-finance-payment"]
        self.assertEqual(finance_payment.classification.transaction_type, TransactionType.TRANSFER)
        self.assertEqual(finance_payment.transaction.linked_transaction_id, "tx-asset")
        self.assertEqual(self.result.summary.asset_purchases, Decimal("2000.00"))

    def test_transfer_is_not_revenue_or_operating_expense(self) -> None:
        transfer = self.entries["tx-transfer"]
        self.assertEqual(transfer.classification.transaction_type, TransactionType.TRANSFER)
        self.assertNotIn("tx-transfer", self.result.reconciliation.unrecorded_income)
        self.assertEqual(self.result.summary.revenue, Decimal("1850.00"))
        self.assertEqual(self.result.summary.operating_expenses, Decimal("592.50"))

    def test_invoice_creation_is_not_revenue(self) -> None:
        unpaid = next(invoice for invoice in self.result.invoices if invoice.invoice_id == "INV-SYN-103")
        self.assertEqual(unpaid.status.value, "Sent")
        self.assertEqual(unpaid.income_transaction_id, None)
        self.assertEqual(self.result.summary.revenue, Decimal("1850.00"))
        self.assertEqual(self.result.summary.outstanding_invoices, 1)

    def test_paid_invoice_links_to_actual_income_transaction(self) -> None:
        paid = next(invoice for invoice in self.result.invoices if invoice.invoice_id == "INV-SYN-102")
        income = self.entries[paid.income_transaction_id]
        self.assertEqual(income.classification.transaction_type, TransactionType.INCOME)
        self.assertEqual(income.transaction.amount, paid.amount)
        self.assertEqual(income.transaction.invoice_id, paid.invoice_id)

    def test_missing_receipt_is_flagged_without_removing_ledger_record(self) -> None:
        self.assertIn("tx-office", self.entries)
        self.assertEqual(self.entries["tx-office"].document_status.value, "Missing")
        self.assertEqual(self.result.reconciliation.missing_receipts, ("tx-office",))

    def test_receipt_matches_transaction_by_reference_and_facts(self) -> None:
        entry = self.entries["tx-software"]
        self.assertEqual(entry.matched_document_id, "doc-software")
        self.assertEqual(entry.document_status.value, "Saved")

    def test_duplicate_transaction_is_flagged_and_not_double_counted(self) -> None:
        self.assertEqual(self.result.reconciliation.duplicates, (("tx-software", "tx-software-copy"),))
        self.assertEqual(self.result.summary.operating_expenses, Decimal("592.50"))

    def test_mixed_use_without_percentage_requires_review(self) -> None:
        entry = self.entries["tx-mixed"]
        self.assertTrue(entry.classification.review_required)
        self.assertIsNone(entry.transaction.business_use_percent)
        self.assertIn("none was inferred", entry.classification.review_reasons[0] + " " + entry.classification.review_reasons[-1])

    def test_statement_only_and_ledger_only_records_are_detected(self) -> None:
        self.assertIn("st-012", self.result.reconciliation.statement_only)
        self.assertIn("tx-cash-expense", self.result.reconciliation.ledger_only)
        self.assertIn("st-012", self.result.reconciliation.unrecorded_income)

    def test_payment_source_mismatch_is_explicit(self) -> None:
        self.assertEqual(self.result.reconciliation.source_mismatches, (("st-006", "tx-travel"),))

    def test_monthly_operating_totals_and_mileage(self) -> None:
        summary = self.result.summary
        self.assertEqual(summary.revenue, Decimal("1850.00"))
        self.assertEqual(summary.operating_expenses, Decimal("592.50"))
        self.assertEqual(summary.net_operating_profit, Decimal("1257.50"))
        self.assertEqual(summary.asset_purchases, Decimal("2000.00"))
        self.assertEqual(summary.business_mileage, Decimal("24.00"))

    def test_audit_records_input_rule_review_and_reconciliation(self) -> None:
        event = next(
            event for event in self.result.audit_events
            if event.get("input_record", {}).get("transaction_id") == "tx-mixed"
        )
        self.assertEqual(event["normalized_values"]["payment_source"], "Joint Personal")
        self.assertEqual(event["classification"]["transaction_type"], "Ordinary Expense")
        self.assertTrue(event["human_review_required"])
        self.assertEqual(event["reconciliation_status"], "Matched")


if __name__ == "__main__":
    unittest.main()
