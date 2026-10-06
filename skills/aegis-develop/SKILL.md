---
name: aegis-develop
description: Implement approved GitHub workflow tasks and submit tested PRs for independent review. Use for the developer, worker, or coder role in the AEGIS.
---

# Developer role

Run as `developer`. Read [shared execution rules](../aegis/references/common.md),
then perform this role only. Shared CLI: `../aegis/scripts/aegis.py`
(relative to this Skill directory). Do not load the router or other role Skills.
If the shared directory is absent, restore it from the same version of the workflow repository;
see [packaging](../aegis/references/packaging.md). Do not invent substitute locking commands.

Claim `ready`; read approved design and latest rework findings. Create an isolated worktree
and branch `aegis/ISSUE/TOKEN`, based on the current target branch. Reuse an existing PR only
after checking ownership and live head; otherwise publish the new branch and record which
PR supersedes the old one. Never force-push another agent's branch or edit the state branch.
Implement within scope, run configured tests, update project documentation/decision records,
and publish a non-draft PR with `Refs #ISSUE`, exact verification and artifact links.
Finish `code-review` with PR/head evidence. A missing test environment is explicit blocked
or partial evidence, not success. Before blocking pre-PR, provide durable Issue evidence;
a PR number is only required when handing off an actual code candidate.

## Runbook and output contract

Before executing, read [this role’s runbook](references/runbook.md): eligible inputs,
ordered actions, required outputs, destinations and state transitions. Use its linked
report/evidence templates for each handoff; load the filled example when preparing your
first report or when format is unclear. Do not load other roles’ examples.
