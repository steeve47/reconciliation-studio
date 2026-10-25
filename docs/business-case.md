# Reconciliation Business Case — Planning Model

## Objective

Explore whether deterministic reconciliation support could reduce manual
handling effort while making exceptions easier to identify and review. This is
a scenario model, not a business case approved by Finance and not a measured
result.

## Baseline to collect

Before a pilot, agree a representative baseline with the process owner:

- Transactions reconciled per period and types of accounts/transactions.
- Manual handling time, including exception research and review.
- Existing error, rework, and exception volumes.
- Staff roles involved, loaded hourly cost source, and process calendar.
- Current systems, controls, operating cost, and implementation dependencies.

Use a documented sampling approach and record the measurement period and data
owner. Do not extrapolate from the synthetic sample.

## Scenario formula

The companion calculator estimates:

```text
Monthly capacity hours =
  monthly transactions
  × manual minutes per transaction
  × assumed time reduction
  × assumed adoption
  ÷ 60

Monthly capacity value = monthly capacity hours × loaded staff cost per hour
Annual capacity value = monthly capacity value × 12
Annual net capacity value = annual capacity value − annual operating estimate
Indicative payback months = implementation estimate ÷ monthly net capacity value
```

The UI uses editable assumptions (including a demonstration scenario of 1,000
transactions/month, 8 minutes/transaction, 40% potential time reduction, and
15,000 TZS/hour). These are illustrative planning values only. Adoption and
cost assumptions must also be replaced with approved, evidenced inputs.

## Interpretation and evidence

Released staff capacity is **not automatically a cash saving**. Report capacity
hours, notional capacity value, cash savings, implementation costs, and
operating costs separately. Recognize cash savings only when Finance can
substantiate an actual budget or expenditure reduction. Capacity value becomes
a realized benefit only when redeployment or other value is evidenced.

For a pilot, compare equivalent batches against a measured baseline; capture
volume, complexity, staffing, exceptions, rework, and processing time; obtain
independent verification of matching accuracy; and record assumptions,
measurement dates, and benefit owners. No target in this project is evidence
that a real organization has achieved it.

## Proposed success criteria

Business and risk owners should approve success criteria before testing.
Candidate pilot criteria include:

- All defined critical synthetic exceptions are detected.
- Every non-match has a reason code and review requirement.
- Invalid inputs in the approved UAT set are rejected with actionable errors.
- Handling time is compared to an agreed, measured baseline.
- Exceptions are dispositioned by an authorized human reviewer.
- Any wider rollout requires documented business-owner and control-owner
  approval.
