# 0003 — AEGIS project and Skill naming

Status: accepted, 2026-10-06. Supersedes naming in decisions 0001 and 0002.

The user selected **AEGIS — Agent Engineering Governance & Integration System**.
The shared Skill is `aegis`. Role Skills use action-oriented names:
`aegis-init`, `aegis-plan`, `aegis-develop`, `aegis-review`, `aegis-qa`.
Canonical CLI roles remain `planner`, `developer`, `reviewer`, `qa`: these identify
responsibilities, while Skill names identify entrypoints. Initializer runs setup, not scan.

The CLI is `scripts/aegis.py`. New target projects use `.github/aegis.json`,
`.github/AEGIS.md`, the `aegis:intake` label, `aegis/ISSUE/TOKEN` task branches,
and `aegis-state:aegis-state.json` for shared coordination. Reports use AEGIS headings.

Earlier decision records retain their original names as historical evidence. Existing
remote state, claims, labels or report history must not be silently reset under a new name.
No remote deployment was performed in this development session. If adopting this rename
on an already initialized target, stop all workers and preserve a snapshot of the original
state and Git history. Move the state branch/file preserving contents, revision, identities,
leases and history; migrate policy/entry paths and intake configuration, then switch all
workers together. Inspect and resolve old active claims before restarting. Never run fresh
initialization alongside old active workers. Old reports remain valid historical records.

No compatibility alias or automatic remote migration is installed by this rename. A target
using old paths must complete a deliberate migration before it can run the new CLI.
