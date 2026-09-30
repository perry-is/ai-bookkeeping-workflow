"""Asset acquisition records; financing payments remain separate events."""

from .models import AssetRecord, LedgerEntry, TransactionType


def build_asset_register(entries: list[LedgerEntry]) -> list[AssetRecord]:
    return [
        AssetRecord(
            transaction_id=entry.transaction.transaction_id,
            purchase_date=entry.transaction.date,
            purchase_cost=entry.transaction.amount,
            payment_source=entry.transaction.payment_source,
            financing_source=entry.transaction.financing_source,
            business_use_percent=entry.transaction.business_use_percent,
            supporting_document_ref=entry.transaction.document_ref,
        )
        for entry in entries
        if entry.classification.transaction_type is TransactionType.ASSET_PURCHASE
        and entry.transaction.amount is not None
    ]
