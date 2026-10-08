# Reviewer: design and code decisions

## Read these inputs

1. Read project policy, architecture and acceptance criteria. Scan `--role reviewer`.
2. `design-review`: read the latest planner handoff, exact design version, original Issue,
   dependency evidence and prior design findings. Do not load code/QA playbooks.
3. `code-review`: read approved design and design approval, original AC IDs, latest developer
   delivery, current PR diff/head, test logs, changed docs and prior unresolved findings.
4. Verify you are independent from every author of the reviewed material. Missing exact
   source/version means request clarification/block; a PASS label does not supply evidence.

## Actions and deliverables

| Step | Action | Required result / destination |
|---|---|---|
| Claim | Claim `design-review` or `code-review` as independent reviewer | Saved token and source record/version |
| Review design | Evaluate scope, AC feasibility, alternatives, migration and tests | AC checklist and actionable findings |
| Review code | Inspect exact candidate diff and test evidence against design | AC checklist, file/line findings, test gaps |
| Publish | Design: Issue comment. Code: PR review/comment plus Issue link | Review report using template; no anonymous PASS |
| Decide | Design pass→`ready`, changes→`new`; code pass→`testing`, changes→`ready` | Matching evidence JSON and `finish --to STATE` |
| Block | External missing input prevents a decision | Report blocker and `finish --to blocked` |

Review findings carry severity, location, observed behavior, expected behavior and a concrete
verification condition. Preserve F-IDs across rounds; distinguish repaired, unresolved and
new findings. Every AC needs a result. `approve` is permitted only with no unresolved blocking
findings or unverified mandatory criteria. Reviewer may request additional tests without
claiming those tests ran. A new PR head requires another code review.

All evidence requires schema, summary and URL. Design approval uses `kind: design-review`,
`result: approve`, approved `design_ref` and complete AC coverage; use the [design template](../assets/design-evidence.json).
Code approval additionally includes live `pr`, full `head` and matching `reviewed_head`.
Do not modify implementation while reviewing or switch identity to self-approve. If shared
GitHub credentials prevent an official approval, publish evidence and respect the repository's
separate-account gate. A design comment digest/commit that changed must be reviewed again.

## Format rules

Keep every template heading and field. Replace all angle-bracket placeholders. Use `none`
when inapplicable and `unknown — reason` when unobserved; never invent a pass or a URL.
Assign stable acceptance IDs (`AC-1`, …) and finding IDs (`F-1`, …); carry them through
rework. Every report has a unique `record_id` (UUID), role, actor, Issue, UTC timestamp,
and source records. New reports supersede earlier record IDs explicitly; do not edit
old evidence to hide failures. Retain previous records in Issue/PR history.

Publish Markdown first, then put its actual URL in `evidence.json`. Persist the report,
evidence, record ID and claim token in an ignored local directory. Before reposting after
an ambiguous result, search all comment pages for that record ID and reconcile. A record
ID is not a lock or the CLI's generated state operation ID.

JSON templates include the current CLI's required evidence fields. Additional fields carry
handoff context; the CLI does not validate Markdown headings or semantic truth. Independently
check completed reports against the template before submission. Examples are fictional:
`example/taskboard`, Issue #42 and PR #57 do not imply existing GitHub objects; replace all
URLs and SHAs with observed values. Do not execute example project test commands blindly.

Use [report template](../assets/report.md) and compare with [filled example](../examples/report.md).

## Submit the handoff

Copy [evidence template](../assets/evidence.json), replacing placeholder values and PR 0
with observed data. [Filled evidence example](../examples/evidence.json) demonstrates
`finish --to ready --evidence evidence.json`; select the actual outcome's allowed
state from the table above, not the example by default. JSON evidence points to the
published report. It is a local CLI input, not a replacement for the readable report.

For design work, use the [filled design-review example](../examples/design-review.md) and
[design evidence](../examples/design-evidence.json). Here AC `pass` means the design
adequately specifies the criterion and verification plan; it never means unimplemented
behavior has passed runtime tests. For code work, the main example demonstrates a blocking
finding and rework. Retain a snapshot/digest or exact commit reference of reviewed designs.

## Issue comment when the full report is on the PR

Use [Issue handoff template](../assets/issue-handoff.md); see the
[filled handoff](../examples/issue-handoff.md). Keep its record ID, candidate and outcome
identical to the linked full report. A handoff comment requests a transition; only a
successful CLI write confirms it. On an ambiguous finish, retain the report and reconcile
state instead of announcing completion. If publishing the complete report directly on the
Issue (e.g. design review or pre-PR block), do not add a redundant handoff comment.

## Offline review

When explicitly reviewing local artifacts without a registered GitHub task, record
`coordination: not-executed`, file digests and findings locally. Do not invent Issue URLs,
leases or state transitions. Offline approval evaluates the design/code; it does not claim
that coordinated GitHub review or live gates ran. Resume the managed flow only after setup.

## Continued work and current evidence contract

For a follow-up request, use [continuation and revision](../../aegis/references/continuation.md).
Read [evidence versions](../../aegis/references/evidence-v2.md) when preparing a report.
New tasks use v2; every report, including blocked/rework, binds the current requirement
version and digest. Existing v1 tasks remain explicitly legacy; do not rewrite their history.
The JSON examples are fictional and must be filled from the current task.

Check every observable outcome and counterexample against the original user request and current requirement snapshot. A screenshot of a legend is not proof of changed map fills. Publish a concrete mismatch even when all implementation tests pass.
