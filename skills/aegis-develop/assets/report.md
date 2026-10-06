# AEGIS Development v1
- record_id: <UUID>
- role: developer
- actor: <instance ID>
- issue: <Issue URL>
- recorded_at: <UTC ISO 8601>
- source_records: <approved design and review record IDs/URLs; rework records>
- supersedes: <previous delivery record or none>
- outcome: <review-requested | blocked>
- pr: <PR URL or unknown — reason>
- head: <full SHA or unknown — reason>
- base: <full SHA or unknown — reason>

## Change
<Problem and resulting behavior. Refs #ISSUE.>

## Acceptance results
| ID | Result (pass/fail/unverified) | Evidence |
|---|---|---|
| AC-1 | <result> | <test/log URL and observation> |

## Verification
| Command / check | Environment | Exit / status | Log or artifact |
|---|---|---|---|
| <exact command> | <runtime/OS> | <observed exit> | <durable URL> |

## Documents
| Path | Change and reason |
|---|---|
| <path or none> | <change or explicit no-change reason> |

## Rework resolution
| Finding | Fix / disagreement | Evidence |
|---|---|---|
| <F-ID or none> | <response> | <diff/test link or none> |

## Remaining risks and blockers
<Unverified behavior, blocker, responsible party and required action; or none.>

## Handoff
- next_role: <reviewer | maintainer>
- next_state: <code-review | blocked>
- requested_action: <review exact candidate or resolve blocker>
