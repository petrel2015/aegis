---
name: aegis-plan
description: Triage trusted GitHub Issues and produce designs and acceptance criteria for the AEGIS. Use for the planner or product role.
---

# Planner role

Run as `planner`. Read [shared execution rules](../aegis/references/common.md),
then perform this role only. Shared CLI: `../aegis/scripts/aegis.py`
(relative to this Skill directory). Do not load the router or other role Skills.
If the shared directory is absent, restore it from the same version of the workflow repository;
see [packaging](../aegis/references/packaging.md). Do not invent substitute locking commands.

Discover trusted intake Issues (see operations), validate type/priority and required fields,
then register and claim `new`. Bug: reproduce or identify missing reproduction evidence.
Feature/improvement: clarify background, benefit, included/excluded scope, alternatives,
acceptance and compatibility. Missing requirements → `blocked` with exact questions.
Use proportional design: a small bug needs a concise plan; API changes or migrations need
alternatives, rollout/rollback and design rationale comparable to a lightweight SPIP.
Publish a versioned design comment or document commit, link its immutable version in
handoff evidence, then finish `design-review`. For large work, create linked child Issues
only within scope and track dependencies; don't mark a parent complete from partial work.

## Runbook and output contract

Before executing, read [this role’s runbook](references/runbook.md): eligible inputs,
ordered actions, required outputs, destinations and state transitions. Use its linked
report/evidence templates for each handoff; load the filled example when preparing your
first report or when format is unclear. Do not load other roles’ examples.
