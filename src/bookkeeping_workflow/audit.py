"""Structured, synthetic-only classification and reconciliation audit events."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Invoice, LedgerEntry, ReconciliationResult, StatementEntry, SupportingDocument


def build_audit_events(
    entries: list[LedgerEntry],
    statement: list[StatementEntry],
    documents: list[SupportingDocument],
    invoices: list[Invoice],
    reconciliation: ReconciliationResult,
) -> list[dict[str, Any]]:
    duplicate_ids = {duplicate for _, duplicate in reconciliation.duplicates}
    ledger_only = set(reconciliation.ledger_only)
    mismatched_tx = {transaction_id for _, transaction_id in reconciliation.source_mismatches}
    matched_tx = {transaction_id for _, transaction_id in reconciliation.matched_pairs}
    events = []
    for entry in entries:
        tx = entry.transaction
        events.append({
            "event": "classification_decision",
            "input_record": tx.fact_snapshot(),
            "normalized_values": {
                "date": tx.date,
                "counterparty": tx.counterparty,
                "amount": str(tx.amount) if tx.amount is not None else None,
                "payment_source": tx.payment_source.value if tx.payment_source else None,
            },
            "classification": {
                "transaction_type": entry.classification.transaction_type.value,
                "category": entry.classification.category,
                "rule": entry.classification.rule,
                "ai_suggestion": entry.classification.ai_suggestion,
            },
            "human_review_required": entry.classification.review_required,
            "review_reasons": list(entry.classification.review_reasons),
            "document_status": entry.document_status.value,
            "matched_document_id": entry.matched_document_id,
            "reconciliation_status": (
                "Duplicate" if tx.transaction_id in duplicate_ids
                else "Payment Source Mismatch" if tx.transaction_id in mismatched_tx
                else "Ledger Only" if tx.transaction_id in ledger_only
                else "Duplicate" if tx.transaction_id in duplicate_ids
                else "Matched" if tx.transaction_id in matched_tx
                else "Non-statement Record"
            ),
        })
    statement_by_id = {row.statement_id: row for row in statement}
    for statement_id in reconciliation.statement_only:
        row = statement_by_id[statement_id]
        events.append({
            "event": "statement_exception",
            "input_record": {
                "statement_id": row.statement_id,
                "date": row.date,
                "counterparty": row.counterparty,
                "amount": str(row.amount),
                "direction": row.direction.value if row.direction else None,
                "payment_source": row.payment_source.value if row.payment_source else None,
                "description": row.description,
            },
            "normalized_values": {"date": row.date, "counterparty": row.counterparty, "amount": str(row.amount)},
            "classification": None,
            "human_review_required": True,
            "status": "Unrecorded Income" if row.direction and row.direction.value == "inflow" else "Statement Only",
        })
    for statement_id, transaction_id in reconciliation.source_mismatches:
        row = statement_by_id[statement_id]
        events.append({
            "event": "payment_source_mismatch",
            "statement_record_id": statement_id,
            "ledger_transaction_id": transaction_id,
            "input_record": {
                "statement_id": row.statement_id,
                "date": row.date,
                "counterparty": row.counterparty,
                "amount": str(row.amount),
                "direction": row.direction.value if row.direction else None,
                "payment_source": row.payment_source.value if row.payment_source else None,
                "description": row.description,
            },
            "normalized_values": {
                "date": row.date,
                "counterparty": row.counterparty,
                "amount": str(row.amount),
                "payment_source": row.payment_source.value if row.payment_source else None,
            },
            "classification": None,
            "human_review_required": True,
            "status": "Payment Source Mismatch",
        })
    entries_by_id = {entry.transaction.transaction_id: entry for entry in entries}
    for original_id, duplicate_id in reconciliation.duplicates:
        duplicate = entries_by_id[duplicate_id]
        events.append({
            "event": "possible_duplicate",
            "input_record": duplicate.transaction.fact_snapshot(),
            "normalized_values": {
                "date": duplicate.transaction.date,
                "counterparty": duplicate.transaction.counterparty,
                "amount": str(duplicate.transaction.amount),
                "payment_source": duplicate.transaction.payment_source.value if duplicate.transaction.payment_source else None,
            },
            "classification": {
                "transaction_type": duplicate.classification.transaction_type.value,
                "category": duplicate.classification.category,
                "rule": duplicate.classification.rule,
            },
            "duplicate_of": original_id,
            "human_review_required": True,
            "status": "Possible Duplicate",
        })
    for transaction_id in reconciliation.missing_receipts:
        entry = entries_by_id[transaction_id]
        events.append({
            "event": "missing_documentation",
            "input_record": entry.transaction.fact_snapshot(),
            "normalized_values": {
                "date": entry.transaction.date,
                "counterparty": entry.transaction.counterparty,
                "amount": str(entry.transaction.amount) if entry.transaction.amount is not None else None,
            },
            "classification": {
                "transaction_type": entry.classification.transaction_type.value,
                "category": entry.classification.category,
                "rule": entry.classification.rule,
            },
            "human_review_required": True,
            "status": "Missing Supporting Document",
        })
    for transaction_id in reconciliation.owner_reimbursements_awaiting:
        entry = entries_by_id[transaction_id]
        events.append({
            "event": "reimbursement_follow_up",
            "input_record": entry.transaction.fact_snapshot(),
            "normalized_values": {
                "date": entry.transaction.date,
                "counterparty": entry.transaction.counterparty,
                "amount": str(entry.transaction.amount),
                "payment_source": entry.transaction.payment_source.value if entry.transaction.payment_source else None,
            },
            "classification": {
                "transaction_type": entry.classification.transaction_type.value,
                "category": entry.classification.category,
                "rule": entry.classification.rule,
            },
            "human_review_required": True,
            "status": "Awaiting Reimbursement",
        })
    documents_by_id = {document.document_id: document for document in documents}
    for document_id in reconciliation.orphan_documents:
        document = documents_by_id[document_id]
        events.append({
            "event": "document_exception",
            "input_record": {
                "document_id": document.document_id,
                "vendor": document.vendor,
                "date": document.date,
                "amount": str(document.amount),
                "filename": document.filename,
            },
            "normalized_values": {"date": document.date, "vendor": document.vendor, "amount": str(document.amount)},
            "classification": None,
            "human_review_required": True,
            "status": "No Matching Transaction",
        })
    for invoice in invoices:
        events.append({
            "event": "invoice_lifecycle",
            "input_record": {
                "invoice_id": invoice.invoice_id,
                "counterparty": invoice.counterparty,
                "amount": str(invoice.amount),
                "status": invoice.status.value,
                "issued_date": invoice.issued_date,
                "due_date": invoice.due_date,
                "paid_date": invoice.paid_date,
                "income_transaction_id": invoice.income_transaction_id,
            },
            "normalized_values": {"amount": str(invoice.amount), "status": invoice.status.value},
            "classification": None,
            "human_review_required": False,
            "status": "Invoice only; revenue requires linked cash transaction",
        })
    return events


def write_jsonl(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
