#!/usr/bin/env python3
"""Read-only dependency diagnostics and optional ephemeral IPv4 localhost probe."""
import argparse
import errno
import json
import re
import shutil
import socket
import subprocess
from pathlib import Path

COMMANDS = {'python': ['python3', '--version'], 'git': ['git', '--version'],
            'gh': ['gh', '--version'], 'node': ['node', '--version'],
            'npm': ['npm', '--version']}


def check_tool(name, argv):
    executable = shutil.which(argv[0])
    if executable is None:
        return {'tool': name, 'status': 'missing', 'diagnostic': 'executable_not_found'}
    try:
        result = subprocess.run([executable, *argv[1:]], capture_output=True,
                                text=True, timeout=5, check=False)
    except subprocess.TimeoutExpired:
        return {'tool': name, 'status': 'probe_failed', 'diagnostic': 'version_timeout'}
    except OSError as exc:
        return {'tool': name, 'status': 'probe_failed', 'diagnostic': 'execution_error',
                'errno': exc.errno}
    if result.returncode:
        return {'tool': name, 'status': 'probe_failed', 'diagnostic': 'version_exit',
                'exit_code': result.returncode}
    version = (result.stdout or result.stderr).strip().splitlines()
    return {'tool': name, 'status': 'available', 'version': version[0][:200] if version else None}


def check_localhost():
    """Listen only on 127.0.0.1, kernel-selected port; close even after failure."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
        return {'status': 'available', 'target': '127.0.0.1', 'port': 'ephemeral'}
    except OSError as exc:
        return {'status': 'environment_restricted' if exc.errno in (errno.EPERM, errno.EACCES)
                else 'probe_failed', 'diagnostic': 'localhost_listen_error', 'errno': exc.errno}


def classify_log(content):
    """Identify a listen restriction, never infer a test pass or discount other failures."""
    lines = content.splitlines()
    matches = []
    # Node may print code and syscall in separate adjacent lines. Bound the context
    # to prevent an unrelated EPERM far away from a listen message being classified.
    for index, line in enumerate(lines):
        if not re.search(r'\b(?:EPERM|EACCES)\b|\[Errno (?:1|13)\]', line):
            continue
        nearby = '\n'.join(lines[max(0, index - 3):index + 4])
        if re.search(r'\b(?:listen|bind)\b', nearby, re.IGNORECASE):
            matches.append({'line': index + 1, 'diagnostic': 'listen_permission_denied'})
    return {'category': 'environment_restricted' if matches else 'unknown_test_failure',
            'observations': matches, 'test_result': 'undetermined',
            'scope': 'Recognized diagnostics only; inspect the complete log and every failing test.',
            'next_action': 'Preserve original log; reconcile environment and failures before any explicit retry.'}


def probe(include_localhost=False):
    results = [check_tool(name, argv) for name, argv in COMMANDS.items()]
    listen = check_localhost() if include_localhost else {'status': 'not_requested'}
    failed = any(item['status'] != 'available' for item in results)
    failed |= listen['status'] not in ('available', 'not_requested')
    return {'schema': 'aegis-environment/v1', 'status': 'needs_attention' if failed else 'observed',
            'tools': results, 'localhost': listen,
            'proof': 'Availability/version and optional localhost only; no authentication, project-test or release proof.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--localhost', action='store_true', help='Probe then close an ephemeral local listener')
    parser.add_argument('--log', type=Path, help='Classify an existing UTF-8 log; never execute its contents')
    args = parser.parse_args()
    output = probe(args.localhost)
    if args.log:
        try:
            output['log'] = classify_log(args.log.read_text(encoding='utf-8', errors='replace'))
            output['status'] = 'needs_attention'
        except OSError as exc:
            output['log'] = {'category': 'log_unavailable', 'errno': exc.errno}
            output['status'] = 'needs_attention'
    print(json.dumps(output, indent=2))
    return 1 if output['status'] == 'needs_attention' else 0


if __name__ == '__main__':
    raise SystemExit(main())
