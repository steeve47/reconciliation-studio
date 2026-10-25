# User Acceptance Test Plan and Evidence

## Status

The test suite is automated and reproducible. Its results demonstrate
prototype behavior on the synthetic sample and defined invalid-input cases;
they do not constitute acceptance by a business owner or proof of production
fitness.

## Environment

- Python 3.10 or newer
- Dependencies declared in `requirements-dev.txt`
- Synthetic fixtures in `sample_data/`
- Run with `python -m pytest`

## Acceptance scenarios

| ID | Scenario | Expected outcome |
|---|---|---|
| UAT-01 | Reconcile supplied synthetic sample | 8 distinct references; 3 matched, 2 missing in bank, 1 amount mismatch, 1 missing in ledger, 1 duplicate review |
| UAT-02 | Exact unique reference and amount | `MATCHED_EXACT`; no human review |
| UAT-03 | Duplicate reference in either source | `DUPLICATE_REFERENCE`; review required; no ambiguous match |
| UAT-04 | Amount difference | `AMOUNT_MISMATCH`; exact difference shown; review required |
| UAT-05 | Reference appears in only one source | Directional missing-source reason code |
| UAT-06 | Amounts with equivalent cent values | Matched, without binary floating-point comparison |
| UAT-07 | Missing fields, blank reference, invalid date, missing amount | Actionable validation error |
| UAT-08 | More than two fractional amount digits | Rejected rather than silently rounded |
| UAT-09 | Empty, invalid-encoding, duplicate-header, blank-header, or header-only CSV | Rejected with a readable validation error |
| UAT-10 | Review worksheet generation | Only exceptions included; reviewer/disposition fields are pending/blank |
| UAT-11 | Batch audit manifest | Contains batch ID, rule version, hashes and counts; no transaction reference values |
| UAT-12 | Spreadsheet formula-like CSV text | Dangerous string fields are prefixed in downloadable CSV |
| UAT-13 | Missing source table | Reconciliation is rejected |

## Execution record

Record the date, environment, command, pass/fail summary, tester, and any
defects when running the tests. A passing automated suite is technical
evidence, not user acceptance. Before a real pilot, the business owner should
add scenarios based on actual approved process rules and sign off on expected
outcomes.

## Human UAT evidence template

For each business test, record: test ID, input data reference (not confidential
data in a public portfolio), preconditions, steps, expected result, actual
result, reviewer, date, pass/fail, defect ID, and approval.
