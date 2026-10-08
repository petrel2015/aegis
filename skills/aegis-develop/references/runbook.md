# Coder / developer: approved work → reviewed candidate

## Read these inputs

1. Read project rules, configured test commands and relevant architecture/usage documents.
2. Run `status` and `scan --role developer`. Only registered `ready` tasks without a claim
   are eligible, including those returned for rework. Do not implement `new`, `design-review`,
   `code-review`, `testing`, `blocked` or unregistered Issues.
3. For a selected Issue read its body and linked acceptance criteria, the latest approved
   design version, design-review approval, and dependencies. Follow authoritative state
   history links. Missing approval or unmet dependency → report a blocker, don't infer approval.
4. For rework read the latest code-review/QA findings, prior PR diff and test failures.
   Preserve every AC and finding ID. Also check the live PR head and current base.

## Actions and deliverables

| Step | Action | Required result / destination |
|---|---|---|
| Claim | Claim selected `ready` task, retain token; reread inputs | Input checklist and owned task |
| Prepare | Create token-specific branch/worktree from target base | Isolated checkout, observed base SHA |
| Implement | Implement approved scope; address each finding | Code and meaningful tests; per-finding response |
| Verify | Run configured checks; map every AC to observed evidence | Command, environment, exit code, durable log/artifact; no silent skips |
| Document | Update usage/API/design docs affected by change | Changed paths and rationale, or explicit no-change reason |
| Deliver | Push branch; create/update non-draft PR, `Refs #42` | PR body in template format, exact head/base, Issue handoff link |
| Advance | Publish evidence and `finish --to code-review` | `evidence.json` with actual PR/head and report URL |

Do not use `Closes #42` before workflow finalization. Put the full delivery report in the
PR body or an append-only PR comment; add an Issue comment containing record ID, PR URL,
head SHA, outcome, and next role. Link that report from state evidence. Every new candidate
gets a new report; do not overwrite older test failures. When a project PR template already
exists, keep its required sections and include the AEGIS report as an appended section/comment.

If blocked before a PR exists, use the same report with unknown values as `unknown — reason` (retain any observed base),
record unverified ACs and a concrete requested action; publish on the Issue and finish
`blocked` with JSON containing the task’s evidence schema and requirement version/digest, `result: blocked`, `summary` and the actual report `url` (no invented PR).
Test failure requiring more implementation stays in your claimed `ready` task; repair within
budget. If unable to proceed, publish blocked evidence. You cannot approve your own PR.

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
`finish --to code-review --evidence evidence.json`; select the actual outcome's allowed
state from the table above, not the example by default. JSON evidence points to the
published report. It is a local CLI input, not a replacement for the readable report.

## Coder command sequence

Set `AEGIS` to the shared CLI's absolute path, `REPO` to the verified target, and `ACTOR`
to the persisted instance ID. `ISSUE` comes from the eligible scan result; never hardcode
example #42 into a real run. Read report source URLs from the selected task's state history.

```bash
python3 "$AEGIS" --repo "$REPO" status
python3 "$AEGIS" --repo "$REPO" scan --role developer
python3 "$AEGIS" --repo "$REPO" claim --issue "$ISSUE" --actor "$ACTOR" --role developer
# Save the returned token as TOKEN. Read inputs, implement and verify as above.
python3 "$AEGIS" --repo "$REPO" heartbeat --issue "$ISSUE" --actor "$ACTOR" --token "$TOKEN"
# Publish PR/report first, then fill the local evidence file with the actual report URL/head.
python3 "$AEGIS" --repo "$REPO" finish --issue "$ISSUE" --actor "$ACTOR" --token "$TOKEN" --to code-review --evidence evidence.json
```

Claim can fail after a successful scan because another instance won. Skip that task;
do not start implementation. On lease expiry or uncertain remote outcome read the shared
recovery guide. The commands above omit project-specific git/test/PR commands intentionally:
use the actual target's rules and configured tooling, not a fabricated test recipe.

### Input example

State history for Issue #42 is `ready`, with no claim. Its design-review approval links
record D1 and the original Issue lists AC-1 and AC-2. A previous code review returned
finding F-1 and moved the state back to `ready`. This is eligible rework: read D1, its approval,
the last PR candidate and F-1, then claim and fix F-1. An Issue carrying a `ready` label
but whose authoritative state is `code-review` is not eligible.

### Pre-PR blocker example

If a required private dependency is unavailable, retain the report headings, set
`outcome: blocked`, unavailable candidate fields as `unknown — dependency unavailable` (retain observed base), mark ACs `unverified`,
and request a named maintainer to supply access. Post the report to the Issue. Its JSON is:

```json
{"schema":"aegis-evidence/v2", "requirements_version":1, "requirements_digest":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "result":"blocked", "summary":"Blocked before PR: dependency unavailable; maintainer access required", "url":"https://github.com/example/taskboard/issues/42#issuecomment-106"}
```

Use `finish --to blocked`, not `--to code-review`. The URL here is fictional; use the
actual posted report URL. Do not invent a PR just to complete the normal template.

## Issue comment when the full report is on the PR

Use [Issue handoff template](../assets/issue-handoff.md); see the
[filled handoff](../examples/issue-handoff.md). Keep its record ID, candidate and outcome
identical to the linked full report. A handoff comment requests a transition; only a
successful CLI write confirms it. On an ambiguous finish, retain the report and reconcile
state instead of announcing completion. If publishing the complete report directly on the
Issue (e.g. design review or pre-PR block), do not add a redundant handoff comment.

## Product document content

Preserve existing project documentation conventions. When adding a usage section and the
project has no prescribed shape, use [document section template](../assets/document-section.md)
and [filled section example](../examples/document-section.md). This is user-facing content,
separate from the PR delivery report. For architecture changes, update the actual design/
decision document and link its version from the report; do not dump operational logs into
user documentation. Every new example must describe behavior actually verified on the candidate.

## Continued work and current evidence contract

For a follow-up request, use [continuation and revision](../../aegis/references/continuation.md).
Read [evidence versions](../../aegis/references/evidence-v2.md) when preparing a report.
New tasks use v2; every report, including blocked/rework, binds the current requirement
version and digest. Existing v1 tasks remain explicitly legacy; do not rewrite their history.
The JSON examples are fictional and must be filled from the current task.
