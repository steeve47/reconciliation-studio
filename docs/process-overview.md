# Process Overview

## Current-state problem hypothesis

In a manual bank-to-ledger reconciliation, a finance user typically obtains
two extracts, checks transaction references and amounts, investigates missing
or repeated entries, and records a disposition. This project treats that as a
problem hypothesis to validate with process owners—not a claim about a
particular bank's actual process.

## Proposed prototype workflow

1. Select synthetic demo data or upload a bank statement and ledger CSV.
2. Map the transaction reference, date, amount, and optional description
   columns independently for each source.
3. Validate the selected data and reject malformed or ambiguous input.
4. Compare unique transaction references and amounts to the cent.
5. Flag duplicates, missing records, and amount differences with reason codes.
6. Inspect the outcome summary and result table.
7. Download the full result CSV, human-review worksheet, and batch audit
   manifest.
8. A human reviewer investigates exceptions using approved source evidence.

## Business rules

- References are trimmed and matched as case-sensitive text.
- Dates are parsed and validated but are not currently a matching criterion.
- Amounts are compared as exact integer cents; excess fractional precision is
  rejected.
- Any reference repeated in either source is routed to duplicate review.
- A non-duplicate reference missing on one side receives a directional
  missing-record status.
- Matching references with unequal amounts receive an amount-mismatch status.
- A match means only that the documented fields match; it does not establish
  that a transaction is legitimate, authorized, or correctly posted.

## Roles to agree for a pilot

| Role | Proposed responsibility |
|---|---|
| Reconciliation operator | Supplies approved files, checks mappings, runs the batch |
| Exception reviewer | Investigates flagged records and records evidence and decision |
| Process owner | Approves rules, workflow, control points, and acceptance criteria |
| Finance benefit owner | Validates baseline, costs, and realized-benefit claims |
| Risk/security owner | Approves data handling, access, hosting, and control requirements |

These are proposed role definitions, not assigned individuals or approved
organizational responsibilities.
