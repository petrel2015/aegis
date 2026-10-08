# AEGIS

**Agent Engineering Governance & Integration System**

A portable Skill for GitHub-driven software development across independent agents and machines.

Give an agent this repository URL, the **target project**, and a **role**. It reads the
[Skill](skills/aegis/SKILL.md), discovers eligible Issues,
claims one, and follows the engineering lifecycle:

`Issue → design → independent review → development → code review → serialized QA → protected merge`

```text
Read skills/aegis-develop/SKILL.md from this repository.
Target: https://github.com/OWNER/PROJECT
Role: developer
Actor: agent-dev-01 (optional; generate and persist one if omitted)
Process one eligible task using the target policy; report evidence or a resumable blocker.
You may claim Issues, push task branches, create PRs and post workflow evidence in this target.
```

Each role has a separate Skill: [initializer](skills/aegis-init/SKILL.md),
[planner](skills/aegis-plan/SKILL.md), [developer](skills/aegis-develop/SKILL.md),
[reviewer](skills/aegis-review/SKILL.md), [QA](skills/aegis-qa/SKILL.md).
Known roles bypass the router and load shared invariants plus their own playbook only.
[Install the chosen role alongside the shared core](skills/aegis/references/packaging.md).

Actor IDs identify worker instances, not models, roles, GitHub accounts or credentials.
Examples: `codex-desktop-01`, `zcode-workstation-01`, `claude-review-01`, `hermes-server-01`.
Any agent can take any supported role. Omitted IDs are generated and persisted; parallel
instances need distinct IDs, while resumed work retains its identity. Renaming or changing
models does not make an author an independent reviewer. Host-specific loading remains
subject to verification; these examples are not native compatibility claims.

Requires Python 3.10+, git and authenticated GitHub CLI. No model SDK or central runtime.
The URL does not itself install a skill or schedule an agent: direct reading works, while
native skill discovery and scheduling depend on the host. Missing target/permissions are
reported explicitly.

- [中文与快速开始](README.zh.md)
- [Project setup](skills/aegis/references/setup.md)
- [Roles and merge gates](skills/aegis/references/roles.md)
- [Operations and recovery](skills/aegis/references/operations.md)
- [Architecture decision](docs/decisions/0001-github-coordination.md)
- [Validation and limits](docs/validation.md)

Local tests: `python3 -m unittest discover -s tests -v`.

This is an initial implementation. Offline tests do not establish live GitHub race behavior,
native activation in every agent, or production merge readiness. Run a sandbox lifecycle
before enabling autonomous merges. 

Role-local `references/runbook.md` files define eligible inputs, actions, output destinations
and state transitions. `assets/report.md` and `examples/` define fixed report contracts and
filled fictional examples; execution roles also provide CLI evidence JSON templates. Start
with the [coder runbook](skills/aegis-develop/references/runbook.md). Markdown report format
is an agent obligation; the CLI validates state/candidate fields, not report semantics.

Workflow transitions automatically project to `aegis:STATE` Issue labels and append reason/
evidence comments. Filter `label:aegis:blocked` for blockers. Unrelated labels are preserved.
A committed transition with `sync.status: pending` needs display reconciliation, not repeated
work. See [Issue visibility and recovery](skills/aegis/references/issue-visibility.md).

## Deterministic execution

Policy preflight, trusted Issue intake, dependency/rework gates, versioned evidence,
design digests, exact-candidate CI/review checks and guarded merge-queue admission are
implemented. The [one-shot host adapter](skills/aegis/references/policy-and-runner.md)
provides locking, bounded execution, heartbeat supervision and durable logs without a
model runtime or resident scheduler. See [proof boundaries](docs/validation.md).

## Continued delivery

For follow-up requests use [resume and versioned revisions](skills/aegis/references/continuation.md).
New tasks use [phase-specific evidence](skills/aegis/references/evidence-v2.md), observable
acceptance with counterexamples, mandatory configured verification groups and unique run
artifacts. Existing v1 task history remains explicitly legacy. Publish authorized candidates
with the optional [release Skill](skills/aegis-release/SKILL.md); merge and deployment are
separate records. See [the field-trial decision](docs/decisions/0004-continuation-and-evidence.md).
