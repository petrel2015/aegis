# Phase-specific evidence and reproducible runs

Newly registered tasks use `aegis-evidence/v2`. Copy `requirements.version` and
`requirements.digest` from state into `requirements_version` and `requirements_digest`
in every report, even a blocked/rework report. Never compute them from remembered chat text.
The digest binds the complete registered Issue body. Old tasks lacking `evidence_schema`
remain v1; that compatibility does not upgrade their historical pass claims to v2 proof.

## Acceptance input

Each criterion in the Issue's Acceptance criteria section has this format:

```text
AC-1: Temporal territory fill
Outcome: Actual geographic polygon fills change between sourced dates.
Counterexample: Only the legend, event marker or button changes color.
Verification: Browser comparison of rendered polygon fills at both dates.
```

The CLI checks presence and stable IDs. An independent reviewer checks meaning against the
user's original request. Fields cannot prove semantic correctness merely by being nonempty.

## Evidence results

| Reporting stage | Per-AC result | Meaning |
|---|---|---|
| planner (`new`) | covered | Design explains how the requirement will be met and tested |
| design review | reviewed | Independent reviewer checked design against outcome/counterexample |
| developer (`ready`) | implemented | Candidate implements it; developer verification is linked |
| code review | reviewed | Independent reviewer checked the exact candidate |
| QA / merged completion | verified | Observed acceptance on the bound integration candidate |

Each AC entry has `result`, a concrete `observation`, and durable HTTPS `evidence`.
A covered/reviewed/implemented result is not production acceptance. Overall QA `result`
remains `pass`; review overall `result` remains `approve`. Blocked/rework must not say pass.
Design digest, exact PR/head, base and tested integration commit gates still apply.

## Configured verification groups

Project policy may add mandatory groups; empty groups are invalid. Commands are argv arrays
from trusted policy, never commands extracted from Issues. Run default commands first, then
all groups in policy order. Report each group's name, exact argv, exit code and durable log.

```json
{"verification_groups":{"browser":[["node","tests/browser.mjs"]],"pages-build":[["npm","run","build:pages"]]}}
```

Configure the order for the actual project: build before tests that consume its output.
Policy may require extra environment fields via `verification_environment: ["browser_version", "viewport"]`.
QA also records `run_id` and `environment` with runtime/version, build_mode, and target;
for browser checks include viewport, browser version and URL. A reused QA run ID is rejected.

## Unique artifacts for every attempt

`run_once.py` already isolates host attempts. For role-created screenshots, logs and reports:

```text
python3 skills/aegis/scripts/evidence_store.py new --repo OWNER/REPO --issue N --role qa
```

Save files only inside the returned directory. A retry creates another run, passing
`--retry-of ORIGINAL_RUN_ID`; never overwrite the prior attempt. Prepare metadata JSON with
`candidate_sha` (actual tested integration SHA) and `environment`, then:

```text
python3 skills/aegis/scripts/evidence_store.py seal RUN_DIRECTORY --metadata METADATA_JSON
python3 skills/aegis/scripts/evidence_store.py verify RUN_DIRECTORY
```

Sealing creates a manifest exclusively and refuses replacement. Verification hashes every
recorded file and detects additions, removals and edits. Symlinks are refused. This is
local integrity evidence, not a WORM store or protection against a writer replacing the
manifest itself. Publish the sealed directory as a durable CI/report artifact; record its
actual URL before handoff. Do not upload secrets. Unpublished local files are local proof only.
