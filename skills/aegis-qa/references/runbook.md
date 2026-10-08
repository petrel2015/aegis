# QA: integration evidence and merge observation

## Read these inputs

1. Read project test commands, required checks, merge/release policy and environment rules.
2. Scan `--role qa`; only `testing` or `merge-ready` tasks are eligible. Respect `qa_busy`.
3. For `testing`, read Issue ACs, approved design, latest developer report and independent
   code approval for the current head; fetch live PR base/head and relevant CI evidence.
4. For `merge-ready`, read the QA pass record, exact tested base/head, current PR/queue
   state and verified server rules. Never use a queued event as proof of merge.

## Actions and deliverables

| Step | Action | Required result / destination |
|---|---|---|
| Claim | Claim task and repository-wide QA slot | Saved token; no shared test run before claim |
| Integrate | Fetch current base/head, build integration candidate | Full head/base/tested_commit SHAs, conflict result |
| Test | Execute configured checks and each AC in disposable environment | Commands, exit codes, environment, durable logs and AC matrix |
| Publish | Post report on PR and link from Issue | QA report and evidence JSON |
| Decide | Pass→`merge-ready`; product failure→`ready`; missing environment→`blocked` | `finish` with matching evidence; release slot |
| Merge stage | Claim `merge-ready`, revalidate and follow merge policy | Manual wait / queued / actual merged observation |
| Finalize | Only observed merged PR→`done`, then close Issue | Merge report with merged SHA/time and actual evidence |

Use the QA report template for tests and merge observations. For queued/manual wait,
record outcome, then `release` without `finish done`. A later run reclaims and observes.
For head drift return `ready` for renewed code review. For base drift return `testing`;
provide the latest observed candidate identity and reason, then obtain fresh integration
evidence. `merge-ready` evidence must match preceding review candidate; `done` must match
preceding QA handoff candidate. If APIs refuse a transition (e.g. PR closed unmerged),
preserve the report and use shared recovery guidance; never falsify PR state.

On failure, record exact reproduction, command, expected/actual, relevant logs and AC/F-IDs.
Publish to existing Issue/PR; create a separate bug Issue only when it is genuinely separate
scope and authorized. Rework history remains attached to the original task.

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
`finish --to merge-ready --evidence evidence.json`; select the actual outcome's allowed
state from the table above, not the example by default. JSON evidence points to the
published report. It is a local CLI input, not a replacement for the readable report.

## Merge report variants

For `queued`, copy the QA report, use a new record ID, link the prior QA pass, record the
actual queue/check URL, and leave `merged_commit` and `merged_at` as `none`. Set next state
to `merge-ready (unchanged)` and next action to observe later; call `release`.

For `merged`, retain source QA record and verified head/PR identity; record the actual
merged commit (which may differ from PR head under squash), timestamp and PR URL. Set
next role `none`, next state `done`, and requested action `close Issue with evidence`.
Keep `schema`, exact `acceptance` coverage and JSON `summary`, `url`, `pr`, `head` with the original PR head, not the squash merge SHA.
Only call `finish --to done` after the live API confirms merge. If the PR's head differs
from the approved candidate, stop for reconciliation instead of borrowing prior QA evidence.

For test failure use `outcome: fail`, mark the affected AC as `fail`, and include F-ID,
reproduction and logs. JSON still includes `pr` and current full `head`, but must not carry
`result: pass`. Finish to `ready`, preserving the report for the developer's next run.

## Evidence fields by decision

The JSON asset is specifically the **test-pass → merge-ready** template. Do not copy its
`result: pass` into a failure, blocked or drift report. Every v2 row also requires requirements_version and requirements_digest. Use these field sets:

| Action | Required JSON fields | Result handling |
|---|---|---|
| Test pass → merge-ready | schema, kind, acceptance, tests, run_id, environment, summary, url, pr, head, base, tested_commit, result | result must be pass; all SHAs observed |
| Failure → ready | schema, summary, url, pr, head | Omit result/base/tested_commit unless separately explaining observed data |
| Missing prerequisite → blocked | schema, summary, url, pr, head | Omit result; describe missing evidence in report |
| Base drift → testing | schema, summary, url, pr, head | Omit result; no new test pass is claimed |
| Head drift → ready | schema, summary, url, pr, current head | Omit result; request review of new candidate |
| Observed merge → done | schema, acceptance, summary, url, pr, approved PR head | Omit result; actual merge observation belongs in report |
| Queued / manual wait | No finish JSON; publish report and release | State remains merge-ready |

The helper still requires a live open, non-draft PR for non-done transitions from QA
states. If a deleted/closed/draft PR prevents even recording blocked through `finish`,
publish the diagnostic report and follow recovery; don't invent an open PR to satisfy it.

## Issue comment when the full report is on the PR

Use [Issue handoff template](../assets/issue-handoff.md); see the
[filled handoff](../examples/issue-handoff.md). Keep its record ID, candidate and outcome
identical to the linked full report. A handoff comment requests a transition; only a
successful CLI write confirms it. On an ambiguous finish, retain the report and reconcile
state instead of announcing completion. If publishing the complete report directly on the
Issue (e.g. design review or pre-PR block), do not add a redundant handoff comment.

## Continued work and current evidence contract

For a follow-up request, use [continuation and revision](../../aegis/references/continuation.md).
Read [evidence versions](../../aegis/references/evidence-v2.md) when preparing a report.
New tasks use v2; every report, including blocked/rework, binds the current requirement
version and digest. Existing v1 tasks remain explicitly legacy; do not rewrite their history.
The JSON examples are fictional and must be filled from the current task.

Use all `verification_groups` as well as `test_commands`; groups are mandatory when configured. Use a unique evidence directory per run, preserving screenshots and logs. Record viewport in browser evidence. Do not overwrite a failed run on retry. See [evidence versions](../../aegis/references/evidence-v2.md) for the storage helper.
