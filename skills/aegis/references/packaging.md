# Skill bundle packaging

The repository is a bundle of role entrypoints and one shared core. Each role has its own
SKILL.md and description so hosts can select it without loading other roles' bodies.

For direct URL use, read the chosen role Skill in the checkout. No native installation is
required if the host can read files and run the needed CLI. A URL alone does not schedule
an agent or prove the host's native skill discovery works.

For native installation, preserve sibling paths in the host's configured skill directory:

```text
<skill-root>/
  aegis/   # shared core; required
  aegis-develop/                       # chosen role, for example
```

Copy the **whole shared core directory** plus each desired role directory from the same
repository commit. For all roles copy all seven directories (including optional `aegis-release`) under `skills/`. Do not install
only a role's SKILL.md, flatten paths, or mix versions. A host installer that only copies
one selected folder needs a second install of the core at the sibling location. If the host
cannot preserve sibling resources, use a full repository checkout and direct file reading.

Shared execution rules are loaded by every execution role. Detailed role instructions,
initialization, and recovery are loaded only when needed. The core CLI/assets remain one
source of truth. Installing all roles may add their short discovery descriptions to a
host's context; it does not require loading every role body. Actual host loading behavior
must be verified in that host; no token-count or native-compatibility guarantee is claimed.
