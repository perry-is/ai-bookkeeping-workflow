# Expected synthetic scenario outcomes

Run `bookkeeping-demo` to calculate the full result and audit trail.

- 13 clear classifications are automatically accepted.
- The mixed-use purchase has no business-use percentage and requires human review.
- The Paper Orbit expense is retained in the ledger and flagged for missing documentation.
- The duplicate CloudNine subscription is flagged; only one copy is reconciled to the statement.
- The June 30 client payment appears on the statement but not in the ledger (possible unrecorded income).
- The Cedar Print House cash expense exists in the ledger but not on the statement.
- The Trailway Transit entry matches by date/vendor/amount but has a payment-source mismatch.
- The Paper Lantern document has no matching transaction and is reported as orphan evidence.
- The owner-paid Desk Garden expense is counted once; its reimbursement is excluded from operating expenses.
- The $2,000 laptop is one asset purchase. The $125 financing payment links to it and is not another asset purchase.
- The $300 reserve transfer is neither revenue nor operating expense.
- One $900 invoice remains outstanding; the paid $600 invoice links to one actual income transaction.
- Operating revenue is $1,850.00, operating expenses are $592.50, operational net is $1,257.50, asset purchases are $2,000.00, and mileage is 24 miles.
- The summary reports nine review questions across ambiguity, missing evidence, duplicates, source mismatch, unmatched records, orphan evidence, and reimbursement follow-up.

These are workflow outputs from fictional inputs, not tax or accounting advice.
- Optional: with `--assist`, the mixed-use purchase also carries an AI category suggestion. It stays in review and totals are unchanged.
