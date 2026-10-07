# Planner: intake → design handoff

## Read these inputs

1. Project AGENTS.md, policy and documentation entry; existing architecture and relevant decisions.
2. Open Issues from all pages: only configured trusted intake, excluding PRs. For unregistered
   Issues, run `intake --actor ID` after preflight; it validates author/label, form fields and AC IDs. For registered work,
   use `scan --role planner`; only `new` with no claim is eligible.
3. Feature/improvement: background, benefit, scope, acceptance. Bug: environment, reproduction,
   actual/expected behavior and impact. Missing information is not permission to guess.
4. On rework, read the latest design-review record and all unresolved finding IDs, then the
   exact previous design version. Follow state history URLs, not merely the latest comment.

## Actions and deliverables

| Step | Action | Required result / destination |
|---|---|---|
| Select | Verify intake, priority, dependencies; register once and claim `new` | Saved Issue number, actor, token and source snapshot |
| Analyze | Reproduce bug or define measurable benefit; identify missing facts | Background, scope/exclusions and AC IDs |
| Design | Compare options; map AC IDs to implementation and validation; describe compatibility/rollback | Versioned design document or complete Issue comment using the template |
| Publish | Post design record on Issue; link exact document commit if used | Durable record URL; `evidence.json` |
| Handoff | `finish --to design-review --evidence evidence.json` | Reviewer can reconstruct design without this chat |
| Block | Record missing facts, impact, requested owner/action | Publish same report with `decision: blocked`; `finish --to blocked` |

Suggested design path: `docs/design/issue-42.md`, unless the project already has a convention.
Its content uses the design template below. Publish its exact commit URL and a short Issue
handoff pointing to it. A small change may put the complete design in an Issue comment.
Store a version/content digest locally and supersede via new records; GitHub comments can
be edited, so their URL alone does not prove immutability. Do not edit user-authored Issue
requirements silently. Child Issues need explicit dependencies and their own acceptance.

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
`finish --to design-review --evidence evidence.json`; select the actual outcome's allowed
state from the table above, not the example by default. JSON evidence points to the
published report. It is a local CLI input, not a replacement for the readable report.
