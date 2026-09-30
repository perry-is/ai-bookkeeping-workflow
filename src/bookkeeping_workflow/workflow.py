"""Top-level orchestration for the synthetic bookkeeping scenario."""

from __future__ import annotations

from pathlib import Path

from .assets import build_asset_register
from .audit import build_audit_events
from .classify import Classifier, RuleBasedClassifier
from .documents import match_documents
from .invoices import validate_invoice_links
from .ledger import build_ledger
from .models import WorkflowResult
from .normalize import load_documents, load_invoices, load_statement, load_transactions
from .reconciliation import reconcile
from .reporting import monthly_summary


EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def run_workflow(examples: Path = EXAMPLES, classifier: Classifier | None = None) -> WorkflowResult:
    transactions = load_transactions(examples / "synthetic_transactions.csv")
    statement = load_statement(examples / "synthetic_statement.csv")
    documents = load_documents(examples / "synthetic_documents.json")
    invoices = load_invoices(examples / "synthetic_invoices.json")

    ledger = build_ledger(transactions, classifier or RuleBasedClassifier())
    ledger, missing_receipts, orphan_documents = match_documents(ledger, documents)
    invoice_problems = validate_invoice_links(invoices, ledger)
    reconciliation = reconcile(ledger, statement, missing_receipts, orphan_documents)
    # Invalid paid/unpaid links become explicit review questions without changing facts.
    if invoice_problems:
        from dataclasses import replace
        reconciliation = replace(
            reconciliation,
            review_required=tuple(sorted(set(reconciliation.review_required) | set(invoice_problems))),
        )
    assets = build_asset_register(ledger)
    summary = monthly_summary("2026-06", ledger, invoices, reconciliation)
    events = build_audit_events(ledger, statement, documents, invoices, reconciliation)
    return WorkflowResult(ledger, statement, documents, invoices, assets, reconciliation, summary, events)
