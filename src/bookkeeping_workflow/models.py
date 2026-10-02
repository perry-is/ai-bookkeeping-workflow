"""Typed bookkeeping facts and workflow decisions for the synthetic demo."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum
from typing import Any


class PaymentSource(StrEnum):
    BUSINESS_CHECKING = "Business Checking"
    BUSINESS_CREDIT_CARD = "Business Credit Card"
    OWNER_PERSONAL = "Owner Personal"
    CO_OWNER_PERSONAL = "Co-owner Personal"
    JOINT_PERSONAL = "Joint Personal"
    CASH = "Cash"
    OTHER = "Other"


class Direction(StrEnum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    NONCASH = "noncash"


class BusinessUse(StrEnum):
    FULL = "full"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class DocumentStatus(StrEnum):
    SAVED = "Saved"
    MISSING = "Missing"
    NOT_NEEDED = "Not Needed"


class TransactionType(StrEnum):
    INCOME = "Income"
    ORDINARY_EXPENSE = "Ordinary Expense"
    ASSET_PURCHASE = "Asset Purchase"
    OWNER_CONTRIBUTION = "Owner Contribution"
    REIMBURSEMENT = "Reimbursement"
    OWNER_DRAW = "Owner Draw"
    TRANSFER = "Transfer"
    MILEAGE = "Mileage"
    OTHER_REVIEW_REQUIRED = "Other / Review Required"


class InvoiceStatus(StrEnum):
    DRAFT = "Draft"
    SENT = "Sent"
    PAID = "Paid"
    OVERDUE = "Overdue"
    VOID = "Void"


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    date: str
    counterparty: str
    amount: Decimal | None
    direction: Direction | None
    description: str
    payment_source: PaymentSource | None
    document_type: str | None
    document_ref: str | None
    document_status: DocumentStatus
    business_use: BusinessUse
    business_use_percent: Decimal | None = None
    linked_transaction_id: str | None = None
    invoice_id: str | None = None
    financing_source: str | None = None
    mileage_miles: Decimal | None = None

    def fact_snapshot(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "date": self.date,
            "counterparty": self.counterparty,
            "amount": str(self.amount) if self.amount is not None else None,
            "direction": self.direction.value if self.direction else None,
            "description": self.description,
            "payment_source": self.payment_source.value if self.payment_source else None,
            "document_type": self.document_type,
            "document_ref": self.document_ref,
            "document_status": self.document_status.value,
            "business_use": self.business_use.value,
            "business_use_percent": (
                str(self.business_use_percent) if self.business_use_percent is not None else None
            ),
            "linked_transaction_id": self.linked_transaction_id,
            "invoice_id": self.invoice_id,
            "financing_source": self.financing_source,
            "mileage_miles": str(self.mileage_miles) if self.mileage_miles is not None else None,
        }


@dataclass(frozen=True)
class StatementEntry:
    statement_id: str
    date: str
    counterparty: str
    amount: Decimal
    direction: Direction | None
    payment_source: PaymentSource | None
    description: str


@dataclass(frozen=True)
class SupportingDocument:
    document_id: str
    vendor: str
    date: str
    amount: Decimal
    filename: str


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    counterparty: str
    amount: Decimal
    status: InvoiceStatus
    issued_date: str
    due_date: str
    paid_date: str | None
    income_transaction_id: str | None


@dataclass(frozen=True)
class Classification:
    transaction_type: TransactionType
    category: str | None
    rule: str
    review_required: bool = False
    review_reasons: tuple[str, ...] = ()
    ai_suggestion: str | None = None  # unverified proposal; never counted in totals


@dataclass(frozen=True)
class LedgerEntry:
    transaction: Transaction
    classification: Classification
    matched_document_id: str | None = None
    document_status: DocumentStatus = DocumentStatus.MISSING
    reconciliation_status: str = "Not Reconciled"


@dataclass(frozen=True)
class AssetRecord:
    transaction_id: str
    purchase_date: str
    purchase_cost: Decimal
    payment_source: PaymentSource | None
    financing_source: str | None
    business_use_percent: Decimal | None
    supporting_document_ref: str | None


@dataclass(frozen=True)
class ReconciliationResult:
    matched_pairs: tuple[tuple[str, str], ...] = ()
    statement_only: tuple[str, ...] = ()
    ledger_only: tuple[str, ...] = ()
    source_mismatches: tuple[tuple[str, str], ...] = ()
    duplicates: tuple[tuple[str, str], ...] = ()
    missing_receipts: tuple[str, ...] = ()
    orphan_documents: tuple[str, ...] = ()
    uncategorized: tuple[str, ...] = ()
    review_required: tuple[str, ...] = ()
    owner_reimbursements_awaiting: tuple[str, ...] = ()
    unrecorded_income: tuple[str, ...] = ()
    transfers: tuple[str, ...] = ()
    assets_misclassified: tuple[str, ...] = ()


@dataclass(frozen=True)
class MonthlySummary:
    month: str
    revenue: Decimal
    operating_expenses: Decimal
    net_operating_profit: Decimal
    asset_purchases: Decimal
    business_mileage: Decimal
    missing_receipts: int
    unreconciled_transactions: int
    owner_reimbursements_awaiting: int
    outstanding_invoices: int
    review_questions: int


@dataclass
class WorkflowResult:
    entries: list[LedgerEntry]
    statement: list[StatementEntry]
    documents: list[SupportingDocument]
    invoices: list[Invoice]
    assets: list[AssetRecord]
    reconciliation: ReconciliationResult
    summary: MonthlySummary
    audit_events: list[dict[str, Any]] = field(default_factory=list)
