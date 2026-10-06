# 0001 — Version-checked GitHub state and protected integration

Status: accepted for initial implementation, 2026-10-06.

The design conversation requested an Issue-centered workflow with independent agents,
claiming across machines, design review, and a single integration QA gate. It explicitly
excluded building an IDE or runtime. The repository retains the user's chosen name.

The conversation considered comments, labels and assignees for locks, and earliest-comment
selection. Those are useful displays but lack an atomic compare-and-update ownership
operation. No production trial of those approaches is claimed. We reject them by API
semantics: two agents can both read unlocked state and then both write a claim.

A dedicated `anw-state` branch stores a JSON state file. GitHub Contents updates require
the previous blob SHA; simultaneous updates on that snapshot conflict. Issue ownership,
transition and global QA slot change in one file update. Revision and operation ID keep
history distinguishable and support reconciliation. Git commits preserve historical state.
A single file has contention/size limits but is simpler to operate than a new service.
No automatic retry or stale takeover is performed. Persistent failures become diagnostics.

The lock only fences state updates among cooperative clients. It cannot stop an expired
process executing tests or pushing branches. Therefore stale ownership needs operator
confirmation that old processes stopped; server-side branch rules protect integration.
GitHub writers can alter state and identities, so this is not a hostile multi-tenant lock.

QA records head, base and tested integration commit. A head-only merge API guard cannot
protect a concurrent base movement. Automated merge therefore requires verified GitHub
merge queue and fresh `merge_group` CI. Without that server gate use manual merge; don't
claim the workflow guarantees race-free integration from local checks alone.

References verified during development:

- [Contents API](https://docs.github.com/en/rest/repos/contents)
- [Git references](https://docs.github.com/en/rest/git/refs)
- [gh pr merge](https://cli.github.com/manual/gh_pr_merge)
- [Spark improvement proposals](https://spark.apache.org/improvement-proposals.html)

SPIP motivates proportional background/benefit/alternatives/compatibility analysis;
this project does not import Spark's governance or claim standard status.

Revisit when state approaches 750 KB, contention becomes material, GHES is needed, or
operators require automated crash takeover. Any successor must preserve historical
ownership and candidate evidence, and prove external-effect fencing before auto-takeover.

Historical naming above is retained as originally recorded. Current names and migration
boundaries are defined in [decision 0003](0003-aegis-name.md).
