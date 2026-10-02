# Privacy boundaries

## Demo data

This repository uses synthetic data only. All businesses, counterparties, invoice IDs, amounts, transactions, and document names are fictional. The demo does not connect to bank accounts, Google Drive, email, OCR services, or a cloud LLM provider. The optional `--assist ollama` mode calls a model running on your own machine.

## Data minimization

The prototype uses only fields needed for the workflow: transaction date, counterparty label, amount, short description, payment source, document reference/type, and explicit review/link fields. It does not ingest account or routing numbers, tax identifiers, personal addresses, full statements, card data, or document image contents.

## Model use

The optional assisted classifier sends a model only the vendor, description, and amount of a transaction the rules could not categorize. Payment source, account identifiers, document references, and full source documents stay outside model context. The model proposes; validation and human review decide.

## What this does not guarantee

The demo is not a security-certified financial system. It has no encryption-at-rest design, access-control model, retention policy, secure document store, or production audit hardening. The local JSONL audit file is runtime output and may contain the synthetic records processed by the demo; it is excluded from version control. Do not use this prototype with real financial information.
