# Environment diagnostics

Use this resource when dependency execution or local browser/API tests fail. It does
not replace coordinator `preflight`, authenticated `gh` checks, or project acceptance.
From the shared Skill directory:

```bash
python3 scripts/environment_check.py
python3 scripts/environment_check.py --localhost --log /absolute/path/to/original-test.log
```

The first form checks Python, git, gh, Node and npm availability/version with fixed
argv and a five-second timeout each. It does not install tools, change configuration,
contact GitHub or test credentials. Node/npm may be unnecessary for a Python-only
project: a missing tool is a diagnostic for the operator to reconcile against the
project's actual commands, not an unconditional product rejection.

`--localhost` explicitly probes an ephemeral IPv4 listener on `127.0.0.1`, then closes
it. `EPERM`/`EACCES` is `environment_restricted`; other socket errors are `probe_failed`.
This is local permission observation, not proof that every project server can start.
Exit 1 means a dependency, requested probe or supplied failure log needs attention; JSON retains individual
results. Logs are read as data and their text is never executed or echoed.

`--log` reports nearby listen/bind permission-denial signatures. Its category may be
`environment_restricted`, `unknown_test_failure` or `log_unavailable`. Even when a known
restriction appears, `test_result` stays `undetermined`: unrelated failures may coexist.
Inspect the entire original log and every failed assertion. A missing signature does
not prove an environment is healthy, and this helper does not turn a failed run into a pass.

For example, a Node log containing `listen EPERM ... 127.0.0.1` produces:

```json
{
  "category": "environment_restricted",
  "observations": [{"line": 1, "diagnostic": "listen_permission_denied"}],
  "test_result": "undetermined"
}
```

Preserve the original run/log and record diagnostics in the role report. Reconcile
permissions and remaining defects before an explicit authorized retry; use a new
[evidence run](evidence-v2.md) with its retry relationship. No automatic rerun,
escalation, claim mutation or permission request is performed by this helper.
