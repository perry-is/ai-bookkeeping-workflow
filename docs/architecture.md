# Architecture

## Processing stages

1. **Intake:** read the built-in synthetic transaction CSV, statement CSV, document metadata JSON, and invoice register JSON.
2. **Normalization:** convert dates and currency strings into typed Python values, normalize whitespace, validate enums, and preserve optional source references.
3. **Classification:** apply explicit deterministic rules to select an operational transaction type/category and explain the rule used. No model call occurs.
4. **Validation:** require facts needed for a material decision; flag mixed-use or unclear business use without inventing a percentage.
5. **Ledger view:** retain each normalized transaction exactly once and add classification, document, and review metadata.
6. **Evidence and reconciliation:** match document references, compare ledger records to statement rows, and flag duplicates, source mismatches, and unmatched records.
7. **Reporting and audit:** calculate an operational monthly summary and emit structured events containing input IDs, normalized values, rule, decision, review status, and reconciliation status.

## Boundaries

- **Facts:** normalized date, counterparty, amount, description, payment source, document reference, and links are stored separately from a decision.
- **Classification:** transaction type and category describe operational bookkeeping workflow only.
- **Tax treatment:** not implemented. No deduction, depreciation, Section 179, tax allocation, or filing decision is inferred.
- **Human review:** required when missing facts can materially affect the operational classification or where records disagree.
- **AI extension point:** the `Classifier` protocol can later accept a model-backed implementation. Model output would need schema validation, provenance, and the same review gates. The demo uses `RuleBasedClassifier` only.

## Reconciliation keys

Statement matching uses normalized date, counterparty, and amount to find a candidate. Payment source is compared after candidate matching, so an otherwise matching row with a different source is explicitly reported as a source mismatch. One statement row may match only one ledger row; duplicate ledger rows are not silently consumed as additional matches.

Receipt metadata is matched by document reference and then checked against the transaction date, vendor, and amount. A missing or mismatched document remains a review item. An unreferenced document is reported as an orphan rather than attached speculatively.
