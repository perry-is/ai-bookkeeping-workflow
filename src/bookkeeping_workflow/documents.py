"""Supporting-document matching and completeness checks."""

from __future__ import annotations

from decimal import Decimal

from .models import DocumentStatus, LedgerEntry, SupportingDocument, TransactionType


def match_documents(
    entries: list[LedgerEntry], documents: list[SupportingDocument]
) -> tuple[list[LedgerEntry], tuple[str, ...], tuple[str, ...]]:
    by_id = {document.document_id: document for document in documents}
    referenced: set[str] = set()
    updated: list[LedgerEntry] = []
    missing: list[str] = []
    for entry in entries:
        transaction = entry.transaction
        document = by_id.get(transaction.document_ref or "")
        if document and _matches(entry, document):
            referenced.add(document.document_id)
            updated.append(
                LedgerEntry(
                    transaction,
                    entry.classification,
                    matched_document_id=document.document_id,
                    document_status=DocumentStatus.SAVED,
                    reconciliation_status=entry.reconciliation_status,
                )
            )
            continue

        requires_support = entry.classification.transaction_type in {
            TransactionType.INCOME,
            TransactionType.ORDINARY_EXPENSE,
            TransactionType.ASSET_PURCHASE,
            TransactionType.MILEAGE,
        }
        status = transaction.document_status
        if status is DocumentStatus.SAVED and requires_support:
            status = DocumentStatus.MISSING
        if status is DocumentStatus.MISSING and requires_support:
            missing.append(transaction.transaction_id)
        updated.append(
            LedgerEntry(
                transaction,
                entry.classification,
                matched_document_id=None,
                document_status=(DocumentStatus.NOT_NEEDED if not requires_support else status),
                reconciliation_status=entry.reconciliation_status,
            )
        )
    orphaned = tuple(sorted(document.document_id for document in documents if document.document_id not in referenced))
    return updated, tuple(sorted(set(missing))), orphaned


def _matches(entry: LedgerEntry, document: SupportingDocument) -> bool:
    tx = entry.transaction
    expected_amount = tx.amount if tx.amount is not None else Decimal("0.00")
    return (
        document.date == tx.date
        and document.vendor.casefold() == tx.counterparty.casefold()
        and document.amount == expected_amount
    )
