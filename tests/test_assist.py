from __future__ import annotations

import json
import unittest
from unittest import mock

from bookkeeping_workflow.assist import (
    AssistedClassifier,
    ModelUnavailable,
    OllamaModel,
    build_prompt,
    parse_suggestion,
)
from bookkeeping_workflow.workflow import run_workflow


class ScriptedModel:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.reply


class OfflineModel:
    def complete(self, prompt: str) -> str:
        raise ModelUnavailable("offline")


def entry(result, transaction_id):
    return next(e for e in result.entries if e.transaction.transaction_id == transaction_id)


class AssistedClassifierTests(unittest.TestCase):
    def test_model_is_only_asked_about_what_the_rules_could_not_categorize(self) -> None:
        model = ScriptedModel("Office / Workshop Supplies")
        classifier = AssistedClassifier(model)
        run_workflow(classifier=classifier)
        self.assertEqual(classifier.calls, 1)
        self.assertIn("Mixed personal and business purchase", model.prompts[0])

    def test_suggestion_stays_in_review_and_never_changes_totals(self) -> None:
        baseline = run_workflow()
        assisted = run_workflow(classifier=AssistedClassifier(ScriptedModel("Office / Workshop Supplies")))
        mixed = entry(assisted, "tx-mixed").classification
        self.assertEqual(mixed.ai_suggestion, "Office / Workshop Supplies")
        self.assertIsNone(mixed.category)  # the suggestion is not the category
        self.assertTrue(mixed.review_required)
        self.assertEqual(assisted.summary, baseline.summary)

    def test_reply_outside_allowed_categories_is_rejected(self) -> None:
        result = run_workflow(classifier=AssistedClassifier(ScriptedModel("Groceries, probably")))
        mixed = entry(result, "tx-mixed").classification
        self.assertIsNone(mixed.ai_suggestion)
        self.assertTrue(any("rejected" in reason for reason in mixed.review_reasons))

    def test_unavailable_model_degrades_to_rules_only(self) -> None:
        baseline = run_workflow()
        result = run_workflow(classifier=AssistedClassifier(OfflineModel()))
        self.assertEqual(result.summary, baseline.summary)
        self.assertTrue(any("unavailable" in r for r in entry(result, "tx-mixed").classification.review_reasons))

    def test_prompt_excludes_payment_and_document_details(self) -> None:
        transaction = entry(run_workflow(), "tx-mixed").transaction
        prompt = build_prompt(transaction)
        for private_field in ("Joint Personal", "doc-mixed", "receipt"):
            self.assertNotIn(private_field, prompt)

    def test_suggestion_appears_in_audit_trail(self) -> None:
        result = run_workflow(classifier=AssistedClassifier(ScriptedModel("Marketing")))
        event = next(
            e for e in result.audit_events
            if e["event"] == "classification_decision" and e["input_record"]["transaction_id"] == "tx-mixed"
        )
        self.assertEqual(event["classification"]["ai_suggestion"], "Marketing")
        self.assertIsNone(event["classification"]["category"])


class ParsingTests(unittest.TestCase):
    def test_accepts_exact_category_with_light_punctuation(self) -> None:
        self.assertEqual(parse_suggestion(' "software." '), "Software")

    def test_rejects_anything_else(self) -> None:
        for reply in ("UNKNOWN", "Software or Travel", "Food", ""):
            self.assertIsNone(parse_suggestion(reply))


class OllamaTests(unittest.TestCase):
    def test_posts_to_local_generate_endpoint(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"response": "Travel"}'
        with mock.patch("urllib.request.urlopen", return_value=response) as urlopen:
            reply = OllamaModel("qwen2.5:3b").complete("prompt")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:11434/api/generate")
        self.assertEqual(json.loads(request.data)["model"], "qwen2.5:3b")
        self.assertEqual(reply, "Travel")


if __name__ == "__main__":
    unittest.main()
