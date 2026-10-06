# AEGIS Setup v1
- record_id: <UUID>
- role: initializer
- actor: <instance ID>
- repository: <target URL>
- recorded_at: <UTC ISO 8601>
- source_records: <existing rules/docs revisions>
- supersedes: <previous setup record or none>
- outcome: <configured | partial | blocked>

## Files
| Path | Action (created/preserved/updated) | Reason / commit URL |
|---|---|---|
| <path> | <action> | <reason/link> |

## Policy
- intake: <label/allowed-author policy>
- test_commands: <verified commands or unknown — reason>
- required_checks: <names or unknown — reason>
- merge_mode: <manual | merge-queue>
- budgets: <run duration, rework limit, tasks per run>

## Remote state
- state_branch: <verified URL or unknown — reason>
- native_skill_installation: <observed result or not performed>
- scheduler: <observed result or not configured>

## Validation
| Check | Result | Evidence |
|---|---|---|
| <check> | <pass/fail/not-run> | <artifact or reason> |

## Open items and handoff
| Item | Owner | Required action |
|---|---|---|
| <item or none> | <owner> | <action> |
- next_role: <planner | maintainer>
- next_action: <concrete instruction>
