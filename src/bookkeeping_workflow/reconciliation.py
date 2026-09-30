"""Statement comparison, duplicate checks, and explicit exception lists."""

from __future__ import annotations

from collections import defaultdict

from .models import (
    BusinessUse,
    LedgerEntry,
    ReconciliationResult,
    StatementEntry,
    TransactionType,
)


def reconcile(
    entries: list[LedgerEntry], statement: list[StatementEntry], missing_receipts: tuple[str, ...], orphan_documents: tuple[str, ...]
) -> ReconciliationResult:
    duplicates = _find_duplicates(entries)
    duplicate_ids = {duplicate for _, duplicate in duplicates}
    candidates: dict[tuple[str, str, object, str], list[int]] = defaultdict(list)
    for index, entry in enumerate(entries):
        if entry.transaction.amount is not None and entry.transaction.transaction_id not in duplicate_ids:
            candidates[_match_key(entry.transaction.date, entry.transaction.counterparty, entry.transaction.amount, _direction(entry.transaction.direction))].append(index)

    used_ledger: set[int] = set()
    matched: list[tuple[str, str]] = []
    statement_only: list[str] = []
    source_mismatches: list[tuple[str, str]] = []
    for row in statement:
        key = _match_key(row.date, row.counterparty, row.amount, _direction(row.direction))
        available = [index for index in candidates.get(key, []) if index not in used_ledger]
        if not available:
            statement_only.append(row.statement_id)
            continue
        index = available[0]
        used_ledger.add(index)
        entry = entries[index]
        matched.append((row.statement_id, entry.transaction.transaction_id))
        if row.payment_source != entry.transaction.payment_source:
            source_mismatches.append((row.statement_id, entry.transaction.transaction_id))

    ledger_only = [
        entry.transaction.transaction_id
        for index, entry in enumerate(entries)
        if index not in used_ledger and entry.transaction.transaction_id not in duplicate_ids
        and entry.transaction.amount is not None
    ]
    uncategorized = [
        entry.transaction.transaction_id
        for entry in entries
        if entry.classification.transaction_type is TransactionType.ORDINARY_EXPENSE
        and entry.classification.category is None
        and not entry.classification.review_required
    ]
    review_required = [entry.transaction.transaction_id for entry in entries if entry.classification.review_required]
    awaiting_reimbursement = [
        entry.transaction.transaction_id
        for entry in entries
        if entry.transaction.payment_source is not None
        and entry.transaction.payment_source.value in {"Owner Personal", "Co-owner Personal", "Joint Personal"}
        and entry.classification.transaction_type is TransactionType.ORDINARY_EXPENSE
        and entry.transaction.business_use is BusinessUse.FULL
        and not entry.classification.review_required
        and not any(
            candidate.transaction.linked_transaction_id == entry.transaction.transaction_id
            and candidate.classification.transaction_type is TransactionType.REIMBURSEMENT
            for candidate in entries
        )
    ]
    unrecorded_income = [
        statement_id
        for statement_id in statement_only
        if next((row.direction is not None and row.direction.value == "inflow" for row in statement if row.statement_id == statement_id), False)
    ]
    transfers = [
        entry.transaction.transaction_id
        for entry in entries
        if entry.classification.transaction_type is TransactionType.TRANSFER
    ]
    assets_misclassified = [
        entry.transaction.transaction_id
        for entry in entries
        if "equipment" in entry.transaction.description.casefold()
        and entry.classification.transaction_type is not TransactionType.ASSET_PURCHASE
        and entry.classification.transaction_type is not TransactionType.TRANSFER
    ]
    return ReconciliationResult(
        matched_pairs=tuple(matched),
        statement_only=tuple(sorted(statement_only)),
        ledger_only=tuple(sorted(ledger_only)),
        source_mismatches=tuple(sorted(source_mismatches)),
        duplicates=tuple(sorted(duplicates)),
        missing_receipts=tuple(sorted(missing_receipts)),
        orphan_documents=tuple(sorted(orphan_documents)),
        uncategorized=tuple(sorted(uncategorized)),
        review_required=tuple(sorted(review_required)),
        owner_reimbursements_awaiting=tuple(sorted(awaiting_reimbursement)),
        unrecorded_income=tuple(sorted(unrecorded_income)),
        transfers=tuple(sorted(transfers)),
        assets_misclassified=tuple(sorted(assets_misclassified)),
    )


def _find_duplicates(entries: list[LedgerEntry]) -> list[tuple[str, str]]:
    seen: dict[tuple[object, ...], str] = {}
    duplicates: list[tuple[str, str]] = []
    for entry in entries:
        tx = entry.transaction
        if tx.amount is None:
            continue
        fingerprint = _match_key(tx.date, tx.counterparty, tx.amount, _direction(tx.direction)) + (tx.payment_source.value if tx.payment_source else None,)
        if fingerprint in seen:
            duplicates.append((seen[fingerprint], tx.transaction_id))
        else:
            seen[fingerprint] = tx.transaction_id
    return duplicates


def _match_key(date: str, counterparty: str, amount: object, direction: str) -> tuple[str, str, object, str]:
    return (date, " ".join(counterparty.casefold().split()), amount, direction)


def _direction(direction) -> str:
    return direction.value if direction is not None else "unknown"
