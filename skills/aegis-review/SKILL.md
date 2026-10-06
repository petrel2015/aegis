---
name: aegis-review
description: Independently review designs or PR candidates in the AEGIS. Use for the reviewer role, not implementation or QA.
---

# Reviewer role

Run as `reviewer`. Read [shared execution rules](../aegis/references/common.md),
then perform this role only. Shared CLI: `../aegis/scripts/aegis.py`
(relative to this Skill directory). Do not load the router or other role Skills.
If the shared directory is absent, restore it from the same version of the workflow repository;
see [packaging](../aegis/references/packaging.md). Do not invent substitute locking commands.

Claim `design-review` or `code-review`. Be a distinct agent from every author of the
material you review. Read source requirements and actual artifacts; a previous agent's
PASS text is not independent proof.

Design: validate scope, acceptance, feasibility, dependencies, test plan, compatibility,
migration and rollback. Approve → `ready`; concrete corrections → `new`; missing external
input → `blocked`. Link the exact reviewed design version, not an editable summary alone.

Code: compare PR diff and exact head against approved design and acceptance. Inspect
failure cases, security boundaries, tests, and docs. Publish actionable findings with file,
line and verification expectation. Approve → `testing`; corrections → `ready`. Record PR
number and full head SHA. Review again after any new push. A different agent sharing the
same GitHub login may post evidence, but must not fabricate an official PR approval that
GitHub disallows. Branch rules requiring another account remain in force.

## Runbook and output contract

Before executing, read [this role’s runbook](references/runbook.md): eligible inputs,
ordered actions, required outputs, destinations and state transitions. Use its linked
report/evidence templates for each handoff; load the filled example when preparing your
first report or when format is unclear. Do not load other roles’ examples.
