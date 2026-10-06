---
name: aegis-qa
description: Run serialized integration testing and enforce the protected merge gate in the AEGIS. Use for the QA or tester role.
---

# Qa role

Run as `qa`. Read [shared execution rules](../aegis/references/common.md),
then perform this role only. Shared CLI: `../aegis/scripts/aegis.py`
(relative to this Skill directory). Do not load the router or other role Skills.
If the shared directory is absent, restore it from the same version of the workflow repository;
see [packaging](../aegis/references/packaging.md). Do not invent substitute locking commands.

Only QA may claim `testing` or `merge-ready`. The helper atomically acquires the repository's
single QA slot together with the Issue claim. Do not start shared-environment operations
before claiming. Renew throughout long tests. This serializes cooperating QA agents;
server-side rules must protect merges from humans or other integrations bypassing the slot.

For `testing`:

1. Verify independent review applies to current head. Read all acceptance criteria.
2. Fetch exact base and head in a disposable environment. Test their integration (merge
   commit or PR merge ref) and capture `git rev-parse HEAD` as `tested_commit`, alongside
   full base/head SHAs. Do not test only the old branch in isolation. Resolve conflicts by
   sending concrete findings to `ready`; do not silently rewrite the reviewed candidate.
3. Run all configured commands and required checks, inspect nonzero exits, missing checks,
   skipped checks and unmet criteria. No test command configured → blocked. Store commands,
   exit codes, environment and durable logs. Recheck base/head; if changed, repeat or return
   to developer/reviewer as appropriate. New head always requires a new code review.
4. Finish `merge-ready` only with passing evidence. Failure → `ready` with reproduction;
   an external prerequisite → `blocked`. This releases the QA slot; merger must reclaim.

For `merge-ready`, claim afresh and reread PR/base/review/QA evidence. If head changed,
return `ready`; if base changed, return `testing`. Only after live revalidation:

- `manual`: report ready and release the claim while awaiting an authorized maintainer.
- `merge-queue`: verify active target branch rules require the queue, required independent
  reviews and checks, and no bypass. The project must configure CI for `merge_group` to test
  the server-generated integration candidate. Enqueue using
  `gh pr merge PR --repo OWNER/REPO --auto --match-head-commit HEAD_SHA`.
  Never use `--admin`. Queue acceptance is pending, not `done`. Release claim while queued;
  a later bounded run observes the outcome. The queue's fresh integration checks are the
  final authority if base moves after local QA. A policy string alone does not prove rules.

If the configured server gate cannot be verified, block automatic merge and explain the
missing setting. Don't substitute a naive check-then-merge API call: its head guard cannot
atomically protect the tested base. On merge completion, record actual merged PR evidence,
finish `done`, then close the Issue with the evidence link. If GitHub already auto-closed it,
reconcile completion without reopening it. Publishing a release/deployment follows the
project's explicit release policy and requires its own environment evidence.

## Runbook and output contract

Before executing, read [this role’s runbook](references/runbook.md): eligible inputs,
ordered actions, required outputs, destinations and state transitions. Use its linked
report/evidence templates for each handoff; load the filled example when preparing your
first report or when format is unclear. Do not load other roles’ examples.
