# Privacy boundaries

## Demo data

This repository uses synthetic data only. All businesses, counterparties, invoice IDs, amounts, transactions, and document names are fictional. The demo does not connect to bank accounts, Google Drive, email, OCR services, or an LLM provider.

## Data minimization

The prototype uses only fields needed for the workflow: transaction date, counterparty label, amount, short description, payment source, document reference/type, and explicit review/link fields. It does not ingest account or routing numbers, tax identifiers, personal addresses, full statements, card data, or document image contents.

## Future model use

The current deterministic classifier has no external route. If a model-backed classifier is added later, the integration should receive only the minimum redacted fields needed for its task. Account identifiers and full source documents should remain outside model context. The model should propose values; validation and human review should decide whether material ambiguities are resolved.

## What this does not guarantee

The demo is not a security-certified financial system. It has no encryption-at-rest design, access-control model, retention policy, secure document store, or production audit hardening. The local JSONL audit file is runtime output and may contain the synthetic records processed by the demo; it is excluded from version control. Do not use this prototype with real financial information.
