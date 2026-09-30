"""Operational monthly totals; no tax calculations or allocations."""

from __future__ import annotations

from decimal import Decimal

from .invoices import outstanding_invoices
from .models import Invoice, LedgerEntry, MonthlySummary, ReconciliationResult, TransactionType


ZERO = Decimal("0.00")


def monthly_summary(
    month: str,
    entries: list[LedgerEntry],
    invoices: list[Invoice],
    reconciliation: ReconciliationResult,
) -> MonthlySummary:
    in_month = [entry for entry in entries if entry.transaction.date.startswith(month)]
    duplicate_ids = {duplicate for _, duplicate in reconciliation.duplicates}
    revenue = sum(
        (entry.transaction.amount or ZERO)
        for entry in in_month
        if entry.classification.transaction_type is TransactionType.INCOME
        and not entry.classification.review_required
        and entry.transaction.transaction_id not in duplicate_ids
    )
    expenses = sum(
        (entry.transaction.amount or ZERO)
        for entry in in_month
        if entry.classification.transaction_type is TransactionType.ORDINARY_EXPENSE
        and not entry.classification.review_required
        and entry.transaction.transaction_id not in duplicate_ids
    )
    assets = sum(
        (entry.transaction.amount or ZERO)
        for entry in in_month
        if entry.classification.transaction_type is TransactionType.ASSET_PURCHASE
        and entry.transaction.transaction_id not in duplicate_ids
    )
    miles = sum(
        (entry.transaction.mileage_miles or ZERO)
        for entry in in_month
        if entry.classification.transaction_type is TransactionType.MILEAGE
    )
    unreconciled_count = len(reconciliation.statement_only) + len(reconciliation.ledger_only) + len(reconciliation.source_mismatches)
    review_count = (
        len(set(reconciliation.review_required) | set(reconciliation.uncategorized) | set(reconciliation.assets_misclassified))
        + len(reconciliation.statement_only)
        + len(reconciliation.ledger_only)
        + len(reconciliation.source_mismatches)
        + len(reconciliation.duplicates)
        + len(reconciliation.missing_receipts)
        + len(reconciliation.orphan_documents)
        + len(reconciliation.owner_reimbursements_awaiting)
    )
    return MonthlySummary(
        month=month,
        revenue=revenue,
        operating_expenses=expenses,
        net_operating_profit=revenue - expenses,
        asset_purchases=assets,
        business_mileage=miles,
        missing_receipts=len(reconciliation.missing_receipts),
        unreconciled_transactions=unreconciled_count,
        owner_reimbursements_awaiting=len(reconciliation.owner_reimbursements_awaiting),
        outstanding_invoices=len(outstanding_invoices(invoices)),
        review_questions=review_count,
    )
