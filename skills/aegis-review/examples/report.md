<!-- Fictional format example, not execution evidence. -->

# AEGIS Review v1
- record_id: 33333333-3333-4333-8333-333333333333
- role: reviewer
- actor: claude-review-01
- issue: https://github.com/example/taskboard/issues/42
- recorded_at: 2026-10-06T15:30:00Z
- source_records: development 22222222-2222-4222-8222-222222222222; approved design https://github.com/example/taskboard/issues/42#issuecomment-102
- supersedes: none
- review_kind: code
- reviewed_ref: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
- pr: https://github.com/example/taskboard/pull/57
- decision: changes-requested
- independence: Author zcode-workstation-01; reviewer claude-review-01 did not implement this candidate.

## Acceptance assessment
| ID | Result (pass/fail/unverified) | Evidence / reasoning |
|---|---|---|
| AC-1 | pass | PR selector diff uses filtered rows |
| AC-2 | fail | src/csv.ts:18 strips embedded newlines before quoting |

## Findings
| ID | Severity | Location | Observed vs expected | Required fix and verification | Status |
|---|---|---|---|---|---|
| F-1 | blocking | src/csv.ts:18 | Newline removed; original cell must round-trip | Preserve newline and assert parsed output equals original cell | open |

## Checks performed
Inspected serializer and test fixture. CI run 100 passes but its newline test asserts the
already-normalized value; no independent test execution claimed.

## Handoff
- next_role: developer
- next_state: ready
- requested_action: Repair F-1, add regression assertion, and submit a new candidate for review.
