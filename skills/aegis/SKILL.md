---
name: aegis
description: Select the appropriate role Skill for the GitHub-driven AEGIS when given a repository and role, or help choose a role. Use a dedicated role Skill directly when the role is already known.
---

# AEGIS — Agent Engineering Governance & Integration System

## Workflow entry and shared resources

This is a lightweight router. When the user supplies a role, read **one** matching Skill:

| Role / alias | Skill |
|---|---|
| initializer / setup | [aegis-init](../aegis-init/SKILL.md) |
| planner / product | [aegis-plan](../aegis-plan/SKILL.md) |
| developer / worker / coder | [aegis-develop](../aegis-develop/SKILL.md) |
| reviewer | [aegis-review](../aegis-review/SKILL.md) |
| qa / tester | [aegis-qa](../aegis-qa/SKILL.md) |

If no role can be inferred, ask which role to run. Do not load every role to decide.
Distinguish the skill repository from the target software repository; infer target only
from user input or a verified checkout origin. Ask when missing.

Known roles can enter their Skill directly, bypassing this router. Role Skills share
this directory's `scripts/`, `assets/` and `references/`; they do not copy coordination code.
Keep this core directory alongside any installed role directories at the same version.
See [packaging](references/packaging.md) only when installing or relocating Skills.
