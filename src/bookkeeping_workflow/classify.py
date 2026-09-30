"""Pluggable operational classification interface and deterministic rules."""

from __future__ import annotations

from typing import Protocol

from .models import BusinessUse, Classification, Direction, Transaction, TransactionType


class Classifier(Protocol):
    def classify(self, transaction: Transaction) -> Classification: ...


class RuleBasedClassifier:
    """No model call: simple, inspectable rules for the synthetic scenario."""

    def classify(self, transaction: Transaction) -> Classification:
        description = transaction.description.casefold()
        review_reasons: list[str] = []

        if transaction.mileage_miles is not None:
            kind, category, rule = TransactionType.MILEAGE, "Business Mileage", "mileage field supplied"
        elif "owner contribution" in description:
            kind, category, rule = TransactionType.OWNER_CONTRIBUTION, "Owner Contribution", "explicit owner contribution wording"
        elif "owner draw" in description:
            kind, category, rule = TransactionType.OWNER_DRAW, "Owner Draw", "explicit owner draw wording"
        elif "reimbursement" in description and (
            transaction.linked_transaction_id is not None
            or "reimbursement payout" in description
        ):
            kind, category, rule = TransactionType.REIMBURSEMENT, "Owner Reimbursement", "explicit reimbursement wording"
        elif "transfer" in description or "financing payment" in description:
            kind = TransactionType.TRANSFER
            category = "Financing Payment" if "financing payment" in description else "Transfer"
            rule = "settlement/transfer wording; excluded from operating totals"
        elif any(word in description for word in ("asset purchase", "equipment purchase", "laptop purchase")):
            kind, category, rule = TransactionType.ASSET_PURCHASE, "Equipment", "explicit durable-asset wording"
        elif transaction.direction is Direction.INFLOW:
            kind = TransactionType.INCOME
            category = _income_category(description)
            rule = "inflow classified as operational income"
        elif transaction.direction is Direction.OUTFLOW:
            kind = TransactionType.ORDINARY_EXPENSE
            category = _expense_category(description)
            rule = "outflow classified as ordinary operating expense"
            if category is None:
                review_reasons.append("category is not supported by a clear rule")
        else:
            kind, category, rule = TransactionType.OTHER_REVIEW_REQUIRED, None, "no applicable rule"
            review_reasons.append("transaction type is unclear")

        if transaction.business_use is BusinessUse.MIXED and transaction.business_use_percent is None:
            review_reasons.append("mixed-use percentage is missing; none was inferred")
        elif transaction.business_use is BusinessUse.UNCLEAR:
            review_reasons.append("business use is unclear")
        elif transaction.business_use is BusinessUse.FULL and "personal use" in description:
            review_reasons.append("description suggests personal use; confirm business purpose")

        if transaction.amount is None and transaction.mileage_miles is None:
            review_reasons.append("monetary amount is missing")
        if transaction.direction is None:
            review_reasons.append("transaction direction is missing")
        if transaction.payment_source is None:
            review_reasons.append("payment source is missing")
        if transaction.counterparty == "Unknown / Review":
            review_reasons.append("counterparty is missing")
        if transaction.direction is Direction.INFLOW and transaction.invoice_id and not transaction.invoice_id.startswith("INV-SYN-"):
            review_reasons.append("invoice reference needs validation")

        return Classification(
            transaction_type=(
                TransactionType.OTHER_REVIEW_REQUIRED
                if kind is TransactionType.OTHER_REVIEW_REQUIRED
                else kind
            ),
            category=category,
            rule=rule,
            review_required=bool(review_reasons),
            review_reasons=tuple(review_reasons),
        )


def _income_category(description: str) -> str:
    if "workshop" in description or "teaching" in description:
        return "Teaching / Workshops"
    if "consulting" in description:
        return "Consulting"
    if "coaching" in description:
        return "Coaching"
    return "Other Income"


def _expense_category(description: str) -> str | None:
    rules = (
        (("software", "subscription", "workspace", "domain", "website", "ai service"), "Software"),
        (("office supply", "supplies", "printed", "handout", "workshop materials"), "Office / Workshop Supplies"),
        (("travel", "train", "transit", "hotel", "airfare"), "Travel"),
        (("insurance",), "Insurance"),
        (("utility", "utilities"), "Utilities"),
    )
    for terms, category in rules:
        if any(term in description for term in terms):
            return category
    return None
