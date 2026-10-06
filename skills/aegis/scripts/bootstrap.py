#!/usr/bin/env python3
"""Install project templates without overwriting existing files. No network."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def bootstrap(target):
    target = Path(target).resolve()
    sources = {'.github/aegis.json': ROOT / 'assets/config.json',
               '.github/AEGIS.md': ROOT / 'assets/project-entry.md',
               '.github/pull_request_template.md': ROOT / 'assets/pull_request_template.md'}
    for path in (ROOT / 'assets/ISSUE_TEMPLATE').glob('*.yml'):
        sources['.github/ISSUE_TEMPLATE/' + path.name] = path
    created, existing = [], []
    for name, source in sources.items():
        destination = target / name
        # Do not follow an existing symlink outside the project.
        if not destination.resolve().is_relative_to(target):
            raise ValueError(f'Unsafe destination: {name}')
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open('x') as out:
                out.write(source.read_text())
            created.append(name)
        except FileExistsError:
            existing.append(name)
    return {'created': created, 'preserved': existing,
            'next': 'Read setup reference; configure policy and link .github/AEGIS.md from existing AGENTS.md'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    print(json.dumps(bootstrap(args.target), indent=2))
