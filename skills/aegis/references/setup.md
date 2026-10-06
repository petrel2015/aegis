# Project setup

Use this when initializing or adopting the workflow. Do not overwrite project rules.
If the target was initialized under an earlier project name, complete the
[migration procedure](migration.md) before starting new workers.

1. Verify `git remote get-url origin`, `gh auth status --hostname github.com`, Python >=3.10,
   target write permissions, and a nonempty default branch. The current helper supports
   github.com; GHES is not yet supported. Clone the **skill repository** at an operator-reviewed
   commit, read the selected role SKILL.md, and optionally install the role plus shared core
   as described in [packaging](packaging.md). Direct reading works even without native discovery. Never execute `curl | sh`.
2. Run `python3 /ABS/SKILL/scripts/bootstrap.py /ABS/TARGET`. It preserves existing files.
   Merge preserved templates manually as needed. Add a link to `.github/AEGIS.md`
   in the target's existing AGENTS.md. Avoid replacing the user's document system.
3. Use the project's existing documentation skill if available, otherwise document architecture,
   development/test commands, usage, and significant decisions. This workflow does not require
   DocTrail or another installed skill. Keep README short with links.
4. Configure `.github/aegis.json`: verified test commands, acceptance/CI requirements,
   trusted Issue authors, budgets, intake label, merge policy. Empty `test_commands` means
   unconfigured, never successful. These are agent policy instructions, not a sandbox or a
   configuration executor inside `aegis.py`.
5. Create the intake label using `gh label create aegis:intake --repo OWNER/REPO --color 7057ff`.
   A trusted maintainer applies it to approved Issues. Auto-enrollment can instead allow
   `trusted_issue_authors`; never enroll arbitrary public submissions for privileged execution.
6. After project initialization is authorized, run `aegis.py --repo OWNER/REPO init-remote` once.
   This creates branch `aegis-state` from default and adds `aegis-state.json`. Never merge
   that branch into product code. If initialization is interrupted, inspect the branch/file
   before continuing; an existing branch is an error, not permission to reset state.
7. Select `manual` merge initially, or explicitly configure `merge-queue` after verifying
   active server-side rules, required checks (including `merge_group` CI), approval policy,
   and no bypass. Verify with the actual target repository's settings and a sandbox PR.
   GitHub plan/visibility support varies. Unsupported queue means manual gate, not silent bypass.
8. Commit the project templates through its normal review process. Run a small sandbox Issue
   through all roles and capture links before claiming live readiness.

## Minimal invocation

Give an agent the skill URL plus the following text (replace values):

> Read skills/aegis-develop/SKILL.md from this workflow repository.
> Target: https://github.com/OWNER/PROJECT. Role: developer. Actor: agent-dev-01 (optional; generate and persist one if omitted).
> Follow the target project policy, process at most one eligible task, and report evidence
> or a resumable blocker. You may claim tasks, push task branches, create PRs and post
> workflow evidence in this target. Do not change merge/deployment policy.

For initial setup use `aegis-init`; it runs this setup procedure, not `scan`. For periodic use, configure the host's scheduler to invoke the same bounded
prompt with a stable actor/session identity, no overlapping local run, and a timeout.
Run the cheap CLI `scan` first and invoke the model only if eligible work exists.
Do not install model-specific runtime dependencies into this skill.
