# Initializer: project adoption report

## Read these inputs

1. Verify target origin and operator's setup scope; read existing AGENTS.md, README and docs.
2. Inventory existing Issue/PR templates, test/CI commands, configuration and branch rules.
3. Read only this role's setup reference; no work Issue is claimed and no role scan is needed.
4. Preserve existing files and decisions. Missing test commands or unverified merge rules
   are explicit open configuration items, not defaults that can be reported as ready.

## Actions and deliverables

| Step | Action | Required result / destination |
|---|---|---|
| Inventory | Inspect existing rules, docs, templates and CI | Preserved-file list and missing prerequisites |
| Bootstrap | Run non-overwriting local bootstrap | Created/preserved files, project policy draft |
| Configure | Establish trusted intake, test commands, budgets and merge mode | Reviewed policy paths and actual configured values |
| Initialize | Within authorized target, create state branch once | Verified state branch/file URL or explicit pending action |
| Validate | Check templates/links and sandbox lifecycle if authorized | Observed checks; list live checks not run |
| Deliver | Commit/report through target's normal process | Setup report, exact document commit URLs, unresolved items |

Suggested report location `docs/workflow/setup.md`, or the project's established operations
document; publish via setup PR and link the report in the final response. New docs should
summarize actual architecture/test usage, not fabricated scaffold facts. Initializer does
not call `finish`; `setup-report` is an artifact, not an Issue-state transition. Existing
project rules determine commit/review permissions. Do not claim native host installation
or scheduling unless those steps were actually performed.

## Format rules

Keep every template heading and field. Replace all angle-bracket placeholders. Use `none`
when inapplicable and `unknown — reason` when unobserved; never invent a pass or a URL.
Assign stable acceptance IDs (`AC-1`, …) and finding IDs (`F-1`, …); carry them through
rework. Every report has a unique `record_id` (UUID), role, actor, Issue, UTC timestamp,
and source records. New reports supersede earlier record IDs explicitly; do not edit
old evidence to hide failures. Retain previous records in Issue/PR history.

Publish the setup report through the target project's normal review process, and retain
its record ID and actual URL. Initializer has no Issue claim token or finish evidence JSON. Before reposting after
an ambiguous result, search all comment pages for that record ID and reconcile. A record
ID is not a lock or the CLI's generated state operation ID.

The setup report is a document artifact, not CLI state-transition evidence. Independently
check its fields and actual configuration evidence before submission. Examples are fictional:
`example/taskboard`, Issue #42 and PR #57 do not imply existing GitHub objects; replace all
URLs and SHAs with observed values. Do not execute example project test commands blindly.

Use [report template](../assets/report.md) and compare with [filled example](../examples/report.md).
