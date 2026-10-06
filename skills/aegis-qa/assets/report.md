# AEGIS QA v1
- record_id: <UUID>
- role: qa
- actor: <instance ID>
- issue: <Issue URL>
- recorded_at: <UTC ISO 8601>
- source_records: <approved code review / previous QA record IDs/URLs>
- supersedes: <previous QA record or none>
- pr: <PR URL>
- head: <full SHA>
- base: <full SHA>
- tested_commit: <full SHA or unknown — reason>
- outcome: <pass | fail | blocked | queued | manual-wait | merged>

## Environment and integration
<OS/runtime, disposable environment, merge method and conflict result. No secrets.>

## Acceptance results
| ID | Result (pass/fail/unverified) | Evidence |
|---|---|---|
| AC-1 | <result> | <durable log and observed result> |

## Check results
| Command / required check | Exit / status | Evidence |
|---|---|---|
| <command/check> | <observed value> | <durable URL> |

## Failures and reproduction
<F-ID, reproduction, actual/expected, owner/action; or none.>

## Merge observation
- policy: <manual | merge-queue>
- server_gate_evidence: <rules/check URLs or unknown — reason>
- queue_or_merge_evidence: <actual URL or none>
- merged_commit: <full SHA or none>
- merged_at: <observed UTC time or none>

## Handoff
- next_role: <qa | developer | maintainer | none>
- next_state: <merge-ready | ready | testing | blocked | done; unchanged for queued/manual wait>
- requested_action: <next action>
