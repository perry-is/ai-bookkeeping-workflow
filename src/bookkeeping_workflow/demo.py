"""Human-readable CLI for the fictional monthly bookkeeping workflow."""

from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from .audit import write_jsonl
from .workflow import run_workflow


def money(value: Decimal) -> str:
    return f"${value:,.2f}"


def render(result, audit_path: Path | None) -> str:
    reconciliation = result.reconciliation
    review_ids = set(reconciliation.review_required)
    duplicate_ids = {duplicate for _, duplicate in reconciliation.duplicates}
    missing_ids = set(reconciliation.missing_receipts)
    auto = [
        entry for entry in result.entries
        if not entry.classification.review_required and entry.transaction.transaction_id not in duplicate_ids
    ]
    review = [entry for entry in result.entries if entry.transaction.transaction_id in review_ids]
    summary = result.summary
    lines = [
        "SYNTHETIC BOOKKEEPING WORKFLOW - FICTIONAL JUNE 2026 SCENARIO",
        "",
        f"AUTO-ACCEPTED: {len(auto)}",
        *[f"  {e.transaction.transaction_id}: {e.classification.transaction_type.value} / {e.classification.category or 'Uncategorized'}" for e in auto],
        f"REVIEW REQUIRED: {len(review)}",
        *[f"  {e.transaction.transaction_id}: {'; '.join(e.classification.review_reasons) or 'invoice link needs review'}" for e in review],
        f"MISSING DOCUMENTATION: {len(missing_ids)}",
        *[f"  {identifier}" for identifier in sorted(missing_ids)],
        f"DUPLICATES: {len(reconciliation.duplicates)}",
        *[f"  {first} duplicates {duplicate}" for first, duplicate in reconciliation.duplicates],
        f"UNRECONCILED ITEMS: {len(reconciliation.statement_only) + len(reconciliation.ledger_only) + len(reconciliation.source_mismatches)}",
        *[f"  statement-only: {identifier}" for identifier in reconciliation.statement_only],
        *[f"  ledger-only: {identifier}" for identifier in reconciliation.ledger_only],
        *[f"  payment-source mismatch: {statement_id} vs {transaction_id}" for statement_id, transaction_id in reconciliation.source_mismatches],
        f"OUTSTANDING REIMBURSEMENTS: {len(reconciliation.owner_reimbursements_awaiting)}",
        *[f"  original owner-paid expense: {identifier}" for identifier in reconciliation.owner_reimbursements_awaiting],
        f"OUTSTANDING INVOICES: {summary.outstanding_invoices}",
        *[f"  {invoice.invoice_id}: {invoice.status.value} {money(invoice.amount)}" for invoice in result.invoices if invoice.status.value in {"Draft", "Sent", "Overdue"}],
        f"ORPHAN DOCUMENTS: {len(reconciliation.orphan_documents)}",
        *[f"  {identifier}" for identifier in reconciliation.orphan_documents],
        "",
        f"MONTHLY SUMMARY - {summary.month}",
        f"Revenue: {money(summary.revenue)}",
        f"Operating Expenses: {money(summary.operating_expenses)}",
        f"Net Operating Profit: {money(summary.net_operating_profit)}",
        f"Asset Purchases: {money(summary.asset_purchases)} (separate from operating totals)",
        f"Business Mileage: {summary.business_mileage:.1f} miles",
        f"Missing Receipts: {summary.missing_receipts}",
        f"Unreconciled Transactions: {summary.unreconciled_transactions}",
        f"Owner-paid Expenses Awaiting Reimbursement: {summary.owner_reimbursements_awaiting}",
        f"Outstanding Invoices: {summary.outstanding_invoices}",
        f"Questions / Unusual Items Requiring Review: {summary.review_questions}",
        f"Audit Events: {len(result.audit_events)}",
        f"Audit File: {audit_path.as_posix() if audit_path else '(not written)'}",
        "\nNo tax treatment is calculated. All names and figures are synthetic.",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic bookkeeping workflow.")
    parser.add_argument("--no-audit-file", action="store_true", help="print results without writing local JSONL audit")
    parser.add_argument("--audit-path", type=Path, default=Path(".local/audit.jsonl"))
    args = parser.parse_args()
    result = run_workflow()
    audit_path = None if args.no_audit_file else args.audit_path
    if audit_path:
        write_jsonl(audit_path, result.audit_events)
    print(render(result, audit_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
