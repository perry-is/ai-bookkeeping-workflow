# Business rules represented in the prototype

All amounts and parties in the demo are fictional. These rules define workflow handling, not legal or tax outcomes.

## Facts and classifications

- Normalize date, counterparty, amount, description, payment source, document type/reference, and optional business-use/relationship fields.
- Recognized payment sources are Business Checking, Business Credit Card, Owner Personal, Co-owner Personal, Joint Personal, Cash, and Other.
- Keep normalized input facts separate from operational transaction type/category.
- Types include Income, Ordinary Expense, Asset Purchase, Owner Contribution, Reimbursement, Owner Draw, Transfer, Mileage, and Other / Review Required.
- Unknown or material ambiguity is flagged. The workflow does not invent missing business-use percentages.
- When supplied, `business_use_percent` is a numeric percentage from 0 through 100; a blank field stays unknown.

## Owner-paid expenses and reimbursements

Record the original owner-paid purchase as its original expense and retain the personal payment source. Link a later business reimbursement to that original entry. Reimbursement is a cash/settlement event and is excluded from operating expense totals, so it cannot count the same purchase twice.

## Assets and financing

Record the asset acquisition once with original cost/date, payment source, financing source, and supporting-document reference. Financing payments link back to the asset; they are classified as settlement/transfer workflow events, not new asset purchases. No depreciation or tax treatment is calculated.

## Software and mixed use

Recognizable software/subscription costs can be ordinary expenses when described as business-related. Mixed-use or unclear transactions that require a percentage are flagged for human review; no percentage is inferred.

## Invoices and income

Invoice lifecycle state is separate from a bank/cash transaction. Only an actual income transaction contributes to revenue. A paid invoice must link to an income transaction of the same amount. An unpaid invoice is an outstanding item, not revenue.

## Mileage and documents

Mileage is stored as miles with a mileage-log reference, not as an ordinary vehicle expense. Supporting-document states are Saved, Missing, or Not Needed. Missing documentation does not invalidate a ledger entry and is visibly reported. A document is not considered saved unless matching synthetic document metadata exists and is consistent.

## Reporting

Operating revenue and ordinary operating expenses feed net operating profit. Asset purchases are reported separately. Transfer, reimbursement, financing-payment, and mileage events are not included as operating revenue/expense. Review-required items are listed separately and excluded from accepted operating totals until a person resolves them.
