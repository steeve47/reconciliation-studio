# ClearLedger Reconciliation Studio

A portfolio-ready, rules-based prototype for reconciling a bank statement with
an accounting ledger. Upload two CSVs, map the transaction columns, review
explanations for exceptions, and download reconciliation, review, and batch
traceability files.

> **Demonstration only.** Start with the included synthetic data. Do not upload
> confidential, personal, or real financial data to a public demo. This is not
> an accounting control, production banking system, or source of financial
> advice.

## What it does

- Accepts separate bank-statement and ledger CSV files (up to 20 MB each).
- Maps reference, date, amount, and optional description columns independently.
- Validates required data and reports input errors instead of guessing.
- Matches a unique, case-sensitive transaction reference and exact amount to
  the cent.
- Flags duplicate references, missing records, and amount differences with
  reason codes and human-readable explanations.
- Shows an outcome summary and filterable result table.
- Downloads a result CSV, a human-review worksheet, and a JSON batch manifest
  with rule version, source hashes, and counts.
- Includes a separate editable TZS capacity-planning scenario and governance
  and business-analysis documentation.

The prototype uses deterministic rules and makes **no external AI calls**.
Dates are validated but not used as a matching key. A match is not proof that a
transaction is legitimate or properly authorized.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

If PowerShell blocks environment activation, run the environment's Python
directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit opens the app in a browser. Choose **Synthetic demo data** to explore
the included example, or choose **Upload your CSVs** and provide both files.

## Run automated tests

```powershell
python -m pytest
```

## CSV format

Each file must have one column for each required field:

| Field | Required | Example |
|---|---|---|
| Transaction reference | Yes | `TX-1001` |
| Date | Yes | `2026-10-01` |
| Amount | Yes | `1250.00` |
| Description | No | `Customer payment` |

Column names do not have to match the example: map the correct columns in the
app. References are case-sensitive. Amounts may use comma thousands separators
and a dot decimal separator; amounts with more than two fractional digits are
rejected. Both sources need at least one transaction.

## Matching and exception rules

| Outcome | Rule | Review |
|---|---|---|
| Matched | A reference is unique in each file and amounts agree to the cent | No |
| Duplicate review | Reference occurs more than once in either file | Yes |
| Missing in bank statement | Unique reference exists only in the ledger | Yes |
| Missing in ledger | Unique reference exists only in the bank statement | Yes |
| Amount mismatch | Unique reference occurs in both files but amounts differ | Yes |

The prototype intentionally does not perform fuzzy matching, date matching,
currency conversion, split/combined settlement matching, journal posting, or
payment initiation. Review all exceptions against authorized source records.

## Data handling

The application processes uploads in the running Streamlit instance and does
not write uploaded source files to disk. Downloaded batch metadata includes
SHA-256 hashes, counts, a batch ID, UTC processing timestamp, and rule version;
it excludes transaction values and uploaded filenames. Formula-like text
fields are escaped in CSV downloads. When deployed to a hosted service, files
are still transmitted to that host's server; deployment privacy, retention,
access, and security must be assessed separately.

## Project layout

```text
app.py                           Streamlit application
reconciliation.py                Validation, matching, and export rules
pages/2_Business_Case.py          Editable capacity planning scenario
sample_data/                     Synthetic demo CSVs
tests/                            Reconciliation and app tests
docs/                             Process, UAT, business case, governance, case study
reports/, logs_and_evidence/      Example outputs and portfolio evidence
.github/workflows/tests.yml       Automated tests on pushes and pull requests
requirements*.txt                 Runtime and development dependencies
```

## Portfolio framing

This case study demonstrates a proposed workflow and tested prototype behavior.
It does not claim CRDB or another institution implemented the solution, that a
business user accepted it, or that forecast capacity value became cash
savings. See [`docs/portfolio-case-study.md`](docs/portfolio-case-study.md),
[`docs/responsible-ai-governance.md`](docs/responsible-ai-governance.md), and
[`docs/business-case.md`](docs/business-case.md).

## Publishing to GitHub later

This folder is not initialized as a Git repository, and no GitHub repository
or remote has been created. Before publishing:

1. Review every file, especially `reports/`, `logs_and_evidence/`, and the
   generated governance report, and remove anything you do not intend to share.
   The sample CSVs are synthetic; never add real customer or financial data.
2. Decide whether the repository should be public or private and choose a
   license only if you have the rights and intend to grant those permissions.
   No license has been selected for this project.
3. Create an empty repository on GitHub and upload only the reviewed project
   files. `.gitignore` excludes virtual environments, secrets, and common
   Python test artifacts, but it does not replace a manual review.
4. Confirm the **Tests** workflow passes on the default branch. It is configured
   to run for pushes and pull requests.

Do not publish `.env` files, Streamlit secrets, private reports, or uploaded
source data. A hosted demo receives uploaded files on its server; assess
hosting, access, and retention separately before sharing it publicly.
