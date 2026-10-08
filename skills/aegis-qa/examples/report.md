<!-- Fictional format example, not execution evidence. -->

# AEGIS QA v1
- evidence_schema: aegis-evidence/v2
- requirements_version: 1
- requirements_digest: sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
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


## Original-state replay example (fictional)

F-1 starts with the country panel expanded at 390x844. A normal junction click opens the
popup; its close button should be clickable, but was covered. The retry starts with that
same expanded panel, clicks the same junction, observes the intended automatic collapse,
then closes the popup with a normal click. Manually collapsing first is a workaround and
is not the F-1 retest. Retain both failure and repair evidence URLs in the real report.

## Existing merge authorization example (fictional)

The user has already authorized merging this exact repository's PR. After claiming
merge-ready again, the QA agent rechecks unchanged head/base and passing checks, performs
the authorized manual merge and records the observed merged commit. It does not ask for
identical authorization again or describe the manual action as server-queue protection.
