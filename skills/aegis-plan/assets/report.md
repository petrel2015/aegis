# AEGIS Design v1
- record_id: <UUID>
- role: planner
- actor: <instance ID>
- issue: <Issue URL>
- recorded_at: <UTC ISO 8601>
- source_records: <Issue updated_at / prior design and review record IDs>
- supersedes: <record ID or none>
- decision: <review-requested | blocked>
- type_priority: <feature | bug | improvement>, <P0..P3>

## Background and benefit
<Observed problem, affected users, evidence and expected benefit. For bugs include environment and reproduction.>

## Scope and exclusions
<Included work; explicitly excluded work.>

## Acceptance criteria
| ID | Observable result | Counterexample that fails | Verification method |
|---|---|---|---|
| AC-1 | <specific result> | <misleading substitute> | <test or observable check> |

## Design and alternatives
<Selected approach, affected components, rejected alternatives and reasons.>

## Compatibility and rollback
<API/data changes, migration, rollout and rollback; or none with reason.>

## Dependencies and risks
<Linked dependencies, unresolved facts, impact and mitigation.>

## Rework resolution
| Finding | Response | Evidence / remaining question |
|---|---|---|
| <F-ID or none> | <change or explanation> | <link or none> |

## Handoff
- design_ref: <exact commit URL plus path, or this full design comment's record ID>
- next_role: <reviewer | maintainer>
- next_state: <design-review | blocked>
- requested_action: <review design or resolve named blocker>
