"""CSV/JSON intake and normalization; values are facts, not classifications."""

from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .models import (
    BusinessUse,
    Direction,
    DocumentStatus,
    Invoice,
    InvoiceStatus,
    PaymentSource,
    StatementEntry,
    SupportingDocument,
    Transaction,
)


def _text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _money(value: str | None, *, optional: bool = False) -> Decimal | None:
    raw = _text(value)
    if raw is None:
        if optional:
            return None
        raise ValueError("amount is required")
    try:
        amount = Decimal(raw.replace("$", "").replace(",", "")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount: {raw!r}") from exc
    if amount < 0:
        raise ValueError("amount must be non-negative; direction is a separate field")
    return amount


def _date(value: str | None) -> str:
    raw = _text(value)
    if raw is None:
        raise ValueError("date is required")
    return date.fromisoformat(raw).isoformat()


def load_transactions(path: Path) -> list[Transaction]:
    rows: list[Transaction] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            transaction_id = _text(row.get("transaction_id"))
            if not transaction_id:
                raise ValueError("transaction_id is required")
            amount = _money(row.get("amount"), optional=True)
            mileage = _money(row.get("mileage_miles"), optional=True)
            if mileage is not None and amount is not None:
                raise ValueError("mileage records use mileage_miles, not a monetary amount")
            business_use_percent = _money(row.get("business_use_percent"), optional=True)
            if business_use_percent is not None and business_use_percent > Decimal("100"):
                raise ValueError("business_use_percent must be between 0 and 100")
            rows.append(
                Transaction(
                    transaction_id=transaction_id,
                    date=_date(row.get("date")),
                    counterparty=_text(row.get("counterparty")) or "Unknown / Review",
                    amount=amount,
                    direction=(Direction(_text(row.get("direction"))) if _text(row.get("direction")) else None),
                    description=_text(row.get("description")) or "",
                    payment_source=(PaymentSource(_text(row.get("payment_source"))) if _text(row.get("payment_source")) else None),
                    document_type=_text(row.get("document_type")),
                    document_ref=_text(row.get("document_ref")),
                    document_status=DocumentStatus(_text(row.get("document_status")) or "Missing"),
                    business_use=BusinessUse(_text(row.get("business_use")) or "unclear"),
                    business_use_percent=business_use_percent,
                    linked_transaction_id=_text(row.get("linked_transaction_id")),
                    invoice_id=_text(row.get("invoice_id")),
                    financing_source=_text(row.get("financing_source")),
                    mileage_miles=mileage,
                )
            )
    return rows


def load_statement(path: Path) -> list[StatementEntry]:
    result: list[StatementEntry] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            result.append(
                StatementEntry(
                    statement_id=_text(row.get("statement_id")) or "unknown",
                    date=_date(row.get("date")),
                    counterparty=_text(row.get("counterparty")) or "Unknown",
                    amount=_money(row.get("amount")) or Decimal("0.00"),
                    direction=(Direction(_text(row.get("direction"))) if _text(row.get("direction")) else None),
                    payment_source=(PaymentSource(_text(row.get("payment_source"))) if _text(row.get("payment_source")) else None),
                    description=_text(row.get("description")) or "",
                )
            )
    return result


def load_documents(path: Path) -> list[SupportingDocument]:
    values: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return [
        SupportingDocument(
            document_id=str(row["document_id"]),
            vendor=str(row["vendor"]).strip(),
            date=_date(str(row["date"])),
            amount=_money(str(row["amount"])) or Decimal("0.00"),
            filename=str(row["filename"]).strip(),
        )
        for row in values
    ]


def load_invoices(path: Path) -> list[Invoice]:
    values: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for row in values:
        result.append(
            Invoice(
                invoice_id=str(row["invoice_id"]),
                counterparty=str(row["counterparty"]).strip(),
                amount=_money(str(row["amount"])) or Decimal("0.00"),
                status=InvoiceStatus(str(row["status"])),
                issued_date=_date(str(row["issued_date"])),
                due_date=_date(str(row["due_date"])),
                paid_date=_date(str(row["paid_date"])) if _text(row.get("paid_date")) else None,
                income_transaction_id=_text(row.get("income_transaction_id")),
            )
        )
    return result
