"""A minimal in-memory ledger projection with decision metadata."""

from .classify import Classifier
from .models import LedgerEntry, Transaction


def build_ledger(transactions: list[Transaction], classifier: Classifier) -> list[LedgerEntry]:
    return [LedgerEntry(transaction, classifier.classify(transaction)) for transaction in transactions]
