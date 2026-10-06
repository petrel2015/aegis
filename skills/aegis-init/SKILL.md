---
name: aegis-init
description: Initialize a target GitHub repository for the AEGIS with issue forms, project policy, and shared state. Use for setup or adoption, not for running work items.
---

# Initialize a target project

Distinguish this workflow repository from the target project. Resolve target from the user's
instruction or a verified checkout origin; ask if neither supplies it. Read the target's
AGENTS.md and preserve its rules and existing files.

Follow [project setup](../aegis/references/setup.md).
Use the shared core's bootstrap.py and aegis.py; keep the core directory alongside this Skill
at the same version. Read [packaging](../aegis/references/packaging.md)
only if installing or relocating the bundle. No other role Skill needs to be loaded for setup.
Report files created/preserved, policy still needing configuration, and local versus remote
verification. Setup does not authorize scheduling, deployment, or choosing new credentials.

## Runbook and output contract

Before executing, read [this role’s runbook](references/runbook.md): eligible inputs,
ordered actions, required outputs, destinations and state transitions. Use its linked
report/evidence templates for each handoff; load the filled example when preparing your
first report or when format is unclear. Do not load other roles’ examples.
