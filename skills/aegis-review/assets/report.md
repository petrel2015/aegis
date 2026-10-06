# AEGIS Review v1
- record_id: <UUID>
- role: reviewer
- actor: <instance ID>
- issue: <Issue URL>
- recorded_at: <UTC ISO 8601>
- source_records: <design/development and prior review record IDs/URLs>
- supersedes: <prior review ID or none>
- review_kind: <design | code>
- reviewed_ref: <exact design commit/digest or full PR head SHA>
- pr: <PR URL or none for design>
- decision: <approve | changes-requested | blocked>
- independence: <reviewed authors and confirmation reviewer is not an author>

## Acceptance assessment
| ID | Result (pass/fail/unverified) | Evidence / reasoning |
|---|---|---|
| AC-1 | <result> | <source/diff/test reference> |

## Findings
| ID | Severity | Location | Observed vs expected | Required fix and verification | Status |
|---|---|---|---|---|---|
| <F-1 or none> | <blocking/nonblocking> | <file:line or design section> | <concrete issue> | <testable condition> | <open/resolved> |

## Checks performed
<What was inspected or run, with actual results and links; distinguish not run.>

## Handoff
- next_role: <developer | planner | qa | maintainer>
- next_state: <ready | new | testing | blocked>
- requested_action: <specific next action>
