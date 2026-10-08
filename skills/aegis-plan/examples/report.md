<!-- Fictional format example, not execution evidence. -->

# AEGIS Design v1
- record_id: 11111111-1111-4111-8111-111111111111
- role: planner
- actor: codex-desktop-01
- issue: https://github.com/example/taskboard/issues/42
- recorded_at: 2026-10-06T14:00:00Z
- source_records: Issue updated_at 2026-10-06T13:00:00Z
- supersedes: none
- decision: review-requested
- type_priority: feature, P2

## Background and benefit
Users need to export the currently filtered task list as CSV for offline analysis.

## Scope and exclusions
Export visible rows and columns. Exclude server exports, scheduling and hidden rows.

## Acceptance criteria
| ID | Observable result | Counterexample that fails | Verification method |
|---|---|---|---|
| AC-1 | CSV includes only filtered rows | Download exists but contains hidden rows | Export a fixture with one hidden row |
| AC-2 | Quotes, commas and newlines round-trip correctly | CSV looks readable but splits multiline cells | Parse exported CSV and compare input cells |

## Design and alternatives
Add a pure CSV serializer and a toolbar download action. Reuse the filtered selector.
A server endpoint adds unnecessary infrastructure for the existing client-only dataset.

## Compatibility and rollback
No persisted data or API change. Revert toolbar action and serializer to roll back.

## Dependencies and risks
No external dependencies. CSV escaping can corrupt multiline cells; AC-2 covers this.

## Rework resolution
| Finding | Response | Evidence / remaining question |
|---|---|---|
| none | Initial design | none |

## Handoff
- design_ref: record 11111111-1111-4111-8111-111111111111 (complete design in this comment)
- next_role: reviewer
- next_state: design-review
- requested_action: Review scope, AC coverage and serializer design.
