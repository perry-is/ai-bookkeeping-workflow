"""Optional AI assistance: a model may *suggest* a category. It never decides.

The rules run first. Only when they can't find a category does the model get
asked, and only for that one transaction. Its answer is checked against the
list of allowed categories, attached to the record as a labeled suggestion, and
the record stays in the human review queue. Model output is not a bookkeeping
fact until a person accepts it.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import replace
from typing import Protocol

from .classify import Classifier, RuleBasedClassifier
from .models import Classification, Transaction

ALLOWED_EXPENSE_CATEGORIES = (
    "Software",
    "Office / Workshop Supplies",
    "Travel",
    "Insurance",
    "Utilities",
    "Meals",
    "Marketing",
    "Professional Services",
)


class ModelClient(Protocol):
    def complete(self, prompt: str) -> str: ...


class ModelUnavailable(RuntimeError):
    pass


def build_prompt(transaction: Transaction) -> str:
    # Only the fields needed to judge a category. No payment source, account,
    # document reference, or owner information is sent.
    return (
        "You categorize small-business expenses.\n"
        f"Allowed categories: {', '.join(ALLOWED_EXPENSE_CATEGORIES)}.\n"
        "Reply with exactly one allowed category, or UNKNOWN if none clearly fits.\n\n"
        f"Vendor: {transaction.counterparty}\n"
        f"Description: {transaction.description}\n"
        f"Amount: {transaction.amount}\n"
        "Category:"
    )


def parse_suggestion(reply: str) -> str | None:
    """Accept the reply only if it is exactly an allowed category."""
    cleaned = reply.strip().strip(".\"'").strip()
    for category in ALLOWED_EXPENSE_CATEGORIES:
        if cleaned.casefold() == category.casefold():
            return category
    return None


class AssistedClassifier:
    """Rules first; a model suggestion only where the rules came up empty."""

    def __init__(self, model: ModelClient, rules: Classifier | None = None) -> None:
        self.model = model
        self.rules = rules or RuleBasedClassifier()
        self.calls = 0

    def classify(self, transaction: Transaction) -> Classification:
        decision = self.rules.classify(transaction)
        if decision.category is not None:
            return decision  # rules handled it; the model is never consulted
        self.calls += 1
        try:
            reply = self.model.complete(build_prompt(transaction))
        except ModelUnavailable as exc:
            return replace(decision, review_reasons=(*decision.review_reasons, f"AI suggestion unavailable: {exc}"))
        suggestion = parse_suggestion(reply)
        if suggestion is None:
            note = f"AI reply rejected (not an allowed category): {reply.strip()[:60]!r}"
            return replace(decision, review_reasons=(*decision.review_reasons, note))
        return replace(
            decision,
            ai_suggestion=suggestion,
            review_required=True,
            review_reasons=(*decision.review_reasons, f"AI suggests '{suggestion}'; confirm before accepting"),
        )


class MockModel:
    """Offline stand-in: always proposes the same category so the review path can be shown."""

    def complete(self, prompt: str) -> str:
        return "Office / Workshop Supplies"


class OllamaModel:
    """Calls a local Ollama server; nothing leaves the machine."""

    def __init__(self, model_id: str, base_url: str = "http://localhost:11434", timeout: float = 120.0) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, prompt: str) -> str:
        body = json.dumps({"model": self.model_id, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate", data=body,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ModelUnavailable(str(exc)) from exc
        text = payload.get("response")
        if not isinstance(text, str):
            raise ModelUnavailable("empty response")
        return text
