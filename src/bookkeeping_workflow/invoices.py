"""Invoice lifecycle checks kept separate from cash/income transactions."""

from __future__ import annotations

from .models import Invoice, InvoiceStatus, LedgerEntry, TransactionType


def validate_invoice_links(invoices: list[Invoice], entries: list[LedgerEntry]) -> tuple[str, ...]:
    by_id = {entry.transaction.transaction_id: entry for entry in entries}
    problems: list[str] = []
    for invoice in invoices:
        if invoice.status is InvoiceStatus.PAID:
            entry = by_id.get(invoice.income_transaction_id or "")
            if (
                entry is None
                or entry.classification.transaction_type is not TransactionType.INCOME
                or entry.transaction.amount != invoice.amount
                or entry.transaction.invoice_id != invoice.invoice_id
            ):
                problems.append(invoice.invoice_id)
        elif invoice.income_transaction_id:
            problems.append(invoice.invoice_id)
    return tuple(sorted(problems))


def outstanding_invoices(invoices: list[Invoice]) -> tuple[Invoice, ...]:
    return tuple(
        invoice
        for invoice in invoices
        if invoice.status in {InvoiceStatus.DRAFT, InvoiceStatus.SENT, InvoiceStatus.OVERDUE}
    )
