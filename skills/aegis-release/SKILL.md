---
name: aegis-release
description: Publish an explicitly authorized software candidate and record its build, deployment and live verification evidence. Use for the AEGIS release role after integration, not for code review or permission to change hosting visibility.
---

# Release role

Read the target project's release policy and [release runbook](references/runbook.md).
Keep this directory beside the matching shared `aegis` core.

Release is a separate delivery record; it does not add a claimable state or make `done`
mean deployed. Verify the recorded merge and exact source candidate. When the candidate was
built outside AEGIS, label `execution_mode: external`; never invent a prior QA approval.

Use existing user authorization for the exact destination. Source and artifact repositories
may differ. Keep private source private unless the user authorizes a visibility change.
Inspect provider capabilities before choosing a deployment route. Publish the verified
artifact, then independently check the public version and primary user flow.

Keep pending/failed/remote_unknown distinct from verified. An uncertain deployment is
reconciled using its original operation; do not blindly redeploy to hide uncertainty.

For static Git artifact publication, read [guarded preparation and public verification](references/static-git.md) and use the shared deterministic helper.
