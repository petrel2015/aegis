# 0004 — Continued requirements and phase-specific delivery evidence

Status: accepted for local implementation, 2026-10-08.

## Evidence and problem

ChronoAtlas exposed a semantic acceptance failure: faction-colored event markers satisfied
implementation tests while the user expected changing geographic polygon fills. Subsequent
clarifications added independent collapsible panels and next-major-event playback. Those
later edits were delivered directly rather than through a complete live AEGIS Issue/PR/claim
chain. Product deployment success therefore did not establish AEGIS remote workflow proof.

The previous helper froze Issue bodies and rejected any edit without a revision procedure.
All phases used per-AC pass, conflating planned coverage with verified behavior. QA configured
only default commands; role-created browser artifacts were easy to overwrite. Host runner
attempts already had unique directories; the gap was artifacts created outside that runner.

## Decision

- Add read-only resume diagnostics; the bounded runner calls them before claiming/spawning.
  Direct role Skills require workspace reconciliation. This detects drift but cannot prevent
  a writer bypassing the helper with raw Git; no synthetic retrospective workflow pass.
- Require observable outcome, counterexample and verification method in new intake criteria.
  Structural validation helps completeness; semantic review remains independently required.
- Add explicit CAS-guarded revise. Unleased, noncompleted and nonqueued tasks retain previous
  requirements/history/contributors, increment version and return to new. Invalidate all prior
  phase evidence conservatively rather than guessing a minimal impact graph. Keep rework limits.
- Bind v2 evidence to requirement version/digest and successful predecessor transitions within
  the current epoch. Use covered/reviewed/implemented/verified at the appropriate phase.
  Preserve v1 task compatibility explicitly; new intake and genuine revisions use v2.
- Keep approved review valid across legitimate QA retests for the same candidate. A rejected
  review, failed development or an old epoch cannot be turned into approval through recovery.
- Extend trusted policy with mandatory verification groups and optional required environment
  fields. Preserve original commands and forbid Issue-derived command execution.
- Extend unique run storage to screenshots/logs with exclusive manifests and integrity checks.
  Local integrity is not remote durability or a tamper-proof storage claim.
- Add optional aegis-release and a separate release receipt. Source commit, published artifact,
  deployment and public smoke are distinct observations. Nonverified receipts may retain null
  artifact fields with diagnostics. Receipt validation is structural, not a network probe.

## Alternatives and limits

Automatically treating follow-up chat as approved code, resetting completed Issues, or reusing
old pass records would erase requirements/history. We reject these shortcuts. A generic hosting
runtime and a new always-on coordinator are unnecessary: project release CLIs remain in charge.

Real GitHub race, permissions, queue and multi-host tests remain separate. No live repository
was mutated for this repair. The user authorized AEGIS implementation but did not designate a
new live sandbox for destructive/concurrent workflow tests. See validation.md for actual proof.
