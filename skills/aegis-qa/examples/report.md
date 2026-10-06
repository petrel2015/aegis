<!-- Fictional format example, not execution evidence. -->

# AEGIS QA v1
- record_id: 44444444-4444-4444-8444-444444444444
- role: qa
- actor: hermes-server-01
- issue: https://github.com/example/taskboard/issues/42
- recorded_at: 2026-10-06T16:30:00Z
- source_records: independent code approval https://github.com/example/taskboard/pull/57#issuecomment-104
- supersedes: none
- pr: https://github.com/example/taskboard/pull/57
- head: dddddddddddddddddddddddddddddddddddddddd
- base: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
- tested_commit: cccccccccccccccccccccccccccccccccccccccc
- outcome: pass

## Environment and integration
Disposable Linux container, Node 22. Merged recorded head into recorded base without conflict.

## Acceptance results
| ID | Result (pass/fail/unverified) | Evidence |
|---|---|---|
| AC-1 | pass | https://github.com/example/taskboard/actions/runs/101 — filtered fixture matches |
| AC-2 | pass | https://github.com/example/taskboard/actions/runs/101 — multiline round-trip matches |

## Check results
| Command / required check | Exit / status | Evidence |
|---|---|---|
| npm test -- --run | 0 | https://github.com/example/taskboard/actions/runs/101 |
| Browser export acceptance | pass | https://github.com/example/taskboard/actions/runs/102 |

## Failures and reproduction
None. This standalone QA example assumes the referenced code approval is valid for the recorded head.

## Merge observation
- policy: manual
- server_gate_evidence: unknown — not assessed during this test stage
- queue_or_merge_evidence: none
- merged_commit: none
- merged_at: none

## Handoff
- next_role: qa
- next_state: merge-ready
- requested_action: Reclaim, revalidate head/base and report manual merge readiness. No merge claimed.
