# Responsible AI and Governance Framework

## Status and purpose

This is a proposed governance framework for a portfolio demonstration of
bank-to-ledger reconciliation. It is not an approved policy, production
control, or evidence of deployment at a financial institution.

## System boundary

The prototype applies deterministic, documented matching rules. It does not
use a generative AI model. It does not make payment decisions, approve journal
entries, or resolve an exception on a user's behalf.

| Permitted in this prototype | Out of scope |
|---|---|
| Validate and map the selected transaction fields | Initiate or approve payments |
| Match a unique reference and compare exact amounts to the cent | Post journal entries or alter accounting records |
| Flag missing references, amount differences, and duplicates | Claim financial compliance or production readiness |
| Produce result, review worksheet, and batch-manifest downloads | Infer missing facts or generate ungrounded explanations |
| Support a human review process outside the app | Treat a match as proof that a transaction is legitimate |

## Data protection

- Use the included synthetic CSVs for demonstrations and automated testing.
- Upload only data the user is authorized to process. Do not upload real
  customer or confidential financial data to a public demo.
- The prototype holds uploads in the running app session and does not write
  source files to disk. The batch manifest contains SHA-256 file hashes and row
  counts, not transaction values or uploaded filenames.
- A hosted Streamlit deployment receives uploaded files on its server while
  the session runs. Hosting operators, retention, access, backups, and
  jurisdiction must be assessed separately before any sensitive data is used.
- The CSV exporter prefixes formula-like strings to reduce spreadsheet formula
  injection risk. Always inspect exported content before using it in another
  system.

## Human oversight

- Every result except an exact unique match is explicitly marked for human
  review.
- Duplicate references are ambiguous and are not treated as valid matches.
- The downloadable exception worksheet provides fields for reviewer,
  timestamp, decision, evidence reference, and notes. The worksheet is a
  template; the prototype does not store or enforce review decisions.
- A reviewer must use source records and the applicable finance process to
  make a decision. The software result alone is not approval evidence.

## Risk register

| ID | Risk | Initial rating | Proposed control / evidence |
|---|---|---|---|
| R01 | Incorrect transaction classified as matched | High | Exact reference and amount rules; automated regression tests; independent review of pilot samples |
| R02 | Duplicate records incorrectly matched | High | Detect repeated references in either file and route them to review |
| R03 | Confidential financial data exposed | High | Synthetic data for portfolio use; no source-file persistence; assess deployment, access, and retention before real data |
| R04 | Users rely on a result without checking it | High | Clear exception status, reason code, review worksheet, and explicit boundary messaging |
| R05 | Audit evidence is incomplete | Medium–High | Batch ID, UTC timestamp, rule version, source hashes, counts, and review worksheet |
| R06 | Benefits are overstated | Medium | Separate released capacity from cash savings; measure baseline and pilot results |
| R07 | CSV export triggers spreadsheet formulas | Medium | Escape formula-like text fields and test exported output |
| R08 | Changes introduce regressions | Medium–High | Version control, automated tests, documented review, and deployment checks |

Ratings are initial qualitative assessments for a prototype, not a completed
enterprise risk assessment. A business and risk owner must review and assign
accountability before a real pilot.

## Monitoring and proposed pilot measures

| Measure | How to calculate | Proposed evidence |
|---|---|---|
| Matching accuracy | Correct matches in an independently verified sample ÷ verified automated matches | Business-approved labeled test sample |
| Exception detection | Known exceptions correctly flagged ÷ all known test exceptions | UAT results and expected outcomes |
| Validation effectiveness | Invalid inputs correctly rejected ÷ defined invalid-input cases | Automated validation test report |
| Review completion | Exceptions with a recorded disposition ÷ all exceptions assigned for review | Controlled review log |
| Processing time | Elapsed reconciliation time for comparable batches | Baseline and pilot time study |
| Adoption | Intended users completing the approved workflow ÷ intended users | Pilot task-completion evidence |
| Audit completeness | Results with required traceability fields ÷ total results | Batch manifests and approved review records |

Any targets, including proposed accuracy thresholds, require business-owner
approval and a representative test set. A high match rate alone does not prove
accuracy or legitimacy.

## Release checklist

- [ ] Synthetic test data contains no personal or confidential information.
- [ ] File schema and rule behavior are approved by the process owner.
- [ ] All UAT scenarios have recorded expected results and evidence.
- [ ] Review roles, escalation, data access, retention, and hosting are approved.
- [ ] Exceptions have documented human-review and disposition procedures.
- [ ] Baseline, pilot metrics, owners, and measurement periods are approved.
- [ ] Known limitations and rollback/incident contacts are published.
- [ ] Wider use is blocked until applicable legal, security, risk, and business
  approvals are obtained.
