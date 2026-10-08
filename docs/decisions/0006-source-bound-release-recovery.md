# 0006 — Source-bound release observations and explicit recovery

Status: implemented candidate for Issue #3, 2026-10-08.

ChronoAtlas's successful field release required manual binding of fresh builds, public
artifact commits, deployment jobs, byte verification and browser observations. Legacy
`prepare --source-sha` labels files; v1 receipt validation only checks supplied fields.
Treating either as independent release proof would make a false success easy.

We add small stdlib modules: source build/provenance, finalization, read-only continuation,
sealed evidence publication and append-only report publication. Existing commands remain
compatible and explicitly lower-proof. A release plan pins trusted destination/workflow,
with independent operation records and retained failed attempts. Resume inspects original
objects and never retries a write, redeploys or steals a lock.

Design review F-1 rejected merely trusting a successful Actions job: an ordinary test
could pass without deployment. The approved v2 design also requires the exact Pages
deployment ID, environment, latest success, exact site and same-run log correlation.
Finalization retrieves actual Git tree and completed AEGIS QA/merge identities rather than
accepting a workflow URL as proof. Browser semantics remain project/human observations
subject to independent QA; neither hashes nor JSON fields establish semantic truth.

We rejected a monolithic automatic release loop and a new runtime/database. These commands
coordinate cooperative writers; local reservations and comment markers cannot ensure
server exactly-once execution across competing operation directories. Unknown effects
remain unknown until reconciled. Ignored dependencies remain a reproducibility limit.

Offline tests use real temporary Git sources/bare remotes and injected provider records.
Live self-maintenance records belong to Issue #3; earlier PR ownership is not backfilled.
No product deployment is required or authorized by this implementation exercise.
