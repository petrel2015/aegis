# 0002 — Separate role entrypoints, shared coordination core

Status: accepted, 2026-10-06. Refines entrypoint layout from decision 0001.

The first version placed all playbooks in `references/roles.md` and asked an agent to read
only its section. The user requested distinct role Skills to avoid unrelated context.
A section instruction cannot prevent a file-reading host from loading the whole document.

Each role now has its own SKILL.md: initializer, planner, developer, reviewer and QA.
The original Skill becomes a lightweight router for URL-plus-role requests. Known roles
can enter directly. Execution roles load shared invariants and CLI operations; setup and
recovery are conditional. The old role document remains only a navigation index.

Shared scripts/assets stay in the original core directory. This avoids drift in locking
and state transitions, but role folders are not standalone installation units: install
core plus selected roles as siblings from one commit, or read from a full checkout.
Some hosts expose all installed discovery descriptions; no fixed context savings or
native host compatibility is claimed without measuring that host.

Actor IDs are vendor-neutral instance identities. User-supplied names are optional;
omitted IDs are generated and retained by the host agent. Product names in examples are
human-friendly hints only. Contributors must preserve their identity across retries and
model switches so changing names cannot evade independent review.

Validation: validate each Skill, all relative links, and existing helper tests. No helper
semantics changed in this restructuring. Live host loading remains an external gate.

Historical naming above is retained as originally recorded. Current names and migration
boundaries are defined in [decision 0003](0003-aegis-name.md).
