<!-- Fictional format example, not execution evidence. -->

# AEGIS Setup v1
- record_id: 55555555-5555-4555-8555-555555555555
- role: initializer
- actor: agent-setup-01
- repository: https://github.com/example/taskboard
- recorded_at: 2026-10-06T13:00:00Z
- source_records: README and AGENTS.md in existing target checkout
- supersedes: none
- outcome: partial

## Files
| Path | Action (created/preserved/updated) | Reason / commit URL |
|---|---|---|
| .github/aegis.json | created | Local policy configured; publication pending |
| AGENTS.md | preserved | Existing project instructions retained |

## Policy
- intake: Maintainer applies aegis:intake
- test_commands: npm test -- --run (verified locally)
- required_checks: unknown — target CI not yet inspected
- merge_mode: manual
- budgets: 30 minutes, 3 rework rounds, 1 task per run

## Remote state
- state_branch: unknown — remote initialization not yet performed
- native_skill_installation: not performed
- scheduler: not configured

## Validation
| Check | Result | Evidence |
|---|---|---|
| Local tests | pass | Local setup-test.log, not yet published |
| Remote role lifecycle | not-run | State branch not initialized |

## Open items and handoff
| Item | Owner | Required action |
|---|---|---|
| Remote setup | maintainer | Publish policy, inspect CI and initialize state in authorized target |
- next_role: maintainer
- next_action: Resolve remote prerequisites before starting planner intake.
