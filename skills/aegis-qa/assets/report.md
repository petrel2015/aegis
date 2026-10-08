# AEGIS QA v1
- evidence_schema: aegis-evidence/v2
- requirements_version: <current version from authoritative task>
- requirements_digest: <current sha256 digest from authoritative task>
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
| Failure ID / check | Initial UI state and viewport | Normal action | Expected / actual | Original-step retest and evidence |
|---|---|---|---|---|
| <F-ID or new check> | <open panels, selected item/date, viewport> | <ordinary user input, no forced click> | <expected / observed> | <same starting state and action on repaired candidate; durable URL> |

Record `none` only when no failures occurred. Preserve the original failed run and screenshots.
A workaround that hides the interfering panel, uses force-click or changes the starting
state does not pass the original reproduction. Record workaround checks separately.
Manual scenario observations identify the observer; runner observations identify the command.

## Existing merge authorization
- authorization_ref: <actual user instruction/approved project policy or none>
- scope: <exact repository/PR/destination and remaining limits>
- fresh_revalidation: <claim, current head/base/checks or unverified>


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
