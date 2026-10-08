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
   unconfigured, never successful. `preflight`, `intake`, `claim` and `finish` enforce these gates. The bounded host
   runner enforces time limits; this cooperative protocol is not a sandbox.
5. Create the intake label using `gh label create aegis:intake --repo OWNER/REPO --color 7057ff`.
   A trusted maintainer applies it to approved Issues. State labels (`aegis:new`, `aegis:blocked`, etc.) are created automatically on first synchronization; the runtime needs permission to manage labels and comment on Issues. Auto-enrollment can instead allow
   `trusted_issue_authors`; never enroll arbitrary public submissions for privileged execution.
6. After project initialization is authorized, run `aegis.py --repo OWNER/REPO init-remote` once.
   This creates an orphan branch `aegis-state` containing only `aegis-state.json`. Product
   files and `.github/workflows` are not inherited, so coordination writes do not run
   product CI. Never merge that branch into product code. If initialization is interrupted, inspect the branch/file
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

## Upgrading existing projects to continued-delivery contracts

Bootstrap deliberately preserves existing project files. Compare the new intake templates
with the installed forms and update their Acceptance criteria instructions to include
Outcome, Counterexample and Verification blocks. Review any added verification_groups and
verification_environment fields as trusted project configuration; do not reset existing
commands or permissions. Existing v1 tasks retain their snapshots and evidence schema.
A genuine requirement revision uses the documented revise command; it archives v1 evidence
and adopts v2 without rewriting old records. New registrations require the structured AC
blocks. The optional aegis-release folder needs the same-version shared aegis core.

## Isolating CI on an existing coordination branch

Older initializers copied the default branch, including product Actions workflows.
Plan the migration against the explicitly authorized target:

```sh
python3 /ABS/SKILL/scripts/aegis.py --repo OWNER/REPO isolate-state-ci
```

This command only reads the branch and reports its full head SHA, state revision and
workflow files to remove. Review that list, stop all coordination writers, and release
all claims and the QA slot. Resolve any pending merge queue request before migration.
Then apply the reviewed plan using its exact head:

```sh
python3 /ABS/SKILL/scripts/aegis.py --repo OWNER/REPO isolate-state-ci \
  --apply --expected-head FULL_REVIEWED_SHA --confirm-stopped
```

The migration removes only `.github/workflows` from the coordination branch. It leaves
product branches, other inherited files and the state blob untouched, and adds one
commit whose parent preserves the existing branch history. It refuses stale heads,
claims (including expired claims), occupied QA slots and unresolved queue requests.
Its non-force fast-forward update refuses concurrent state commits. If a mutation
times out or conflicts, inspect the original branch before a fresh plan; never retry
blindly. The result checks that workflows are absent and the state blob is unchanged.
This isolates branch-triggered product workflows; other workflows that explicitly
watch all repository ref events still need project-specific trigger review.

API semantics: [Git trees](https://docs.github.com/en/rest/git/trees#create-a-tree)
and [non-force reference updates](https://docs.github.com/en/rest/git/refs#update-a-reference).
Offline tests exercise request structure, preservation and race refusal. A successful
local mock test does not establish live GitHub permissions or remote readiness.
