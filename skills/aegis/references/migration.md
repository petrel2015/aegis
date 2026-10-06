# Adopting the AEGIS name on an existing target

Fresh projects use `.github/aegis.json`, `.github/AEGIS.md`, `aegis:intake`,
`aegis/ISSUE/TOKEN`, and `aegis-state:aegis-state.json`.

If a target was previously initialized under another name, do not run fresh initialization
alongside old workers. Stop all workers and confirm their child processes have stopped.
Preserve the original state and Git history. Rename the existing state branch/file while
preserving data, revision, contributors, leases and history; migrate configuration/entry
paths and the configured intake label. Switch all workers and Skill directories together
at one version. Inspect and resolve prior active claims before restarting.

Retain old report history and evidence URLs. Do not delete old state to clear failures.
There is no automatic migration or compatibility alias. This procedure requires an
operator-controlled migration in the specific target; the local project rename did not
perform any remote changes.
