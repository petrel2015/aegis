# 0005 — Preserve static publishing contracts and isolate coordination CI

Status: accepted, 2026-10-08.

ChronoAtlas PR #2 exposed inherited product CI on aegis-state updates and a first artifact replacement that omitted ATTRIBUTION.md. The latter was repaired by a new artifact commit; earlier commits and archives were retained. One local API test run failed because the sandbox blocked localhost listening, then passed in an authorized listening environment. These are observed failures, not hypothetical requirements.

Use a state-only orphan branch at initialization, and an explicit existing-branch migration that preserves state bytes, parent history and concurrent-write guards. Do not disable product CI repository-wide. State commits are not product acceptance evidence.

For static Git deployment, prepare a fresh retained archive with a public file inventory and reviewed deletion list. Carry forward domain and attribution/license files. Reject changed protected files for separate review. Verify the public file bytes against the retained archive, then inspect project-specific browser observations and provider job outcome. A helper command exit or build.json alone is insufficient.

Use host/environment diagnostics to retain error classification and original failed attempts; do not silently retry or convert unknown errors to environment success. Evidence version guidance follows actual task snapshots: v2 for new registrations, explicit legacy support for unchanged v1 tasks.

This improves cooperative delivery and repeatability. It does not create hostile-writer locking, automatic deployment authorization, independent factual verification or a universal browser acceptance test. Offline tests and each later live trial are recorded separately in validation.md.
