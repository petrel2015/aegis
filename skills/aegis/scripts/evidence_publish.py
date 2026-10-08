#!/usr/bin/env python3
"""Publish one sealed evidence run once; resume only reconciles its original Git ref."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import evidence_store
from release_support import command, disjoint, fingerprint, read, require, reserve, write


def remote_head(remote, ref):
    lines = command(['git', 'ls-remote', '--refs', remote, ref]).splitlines()
    require(len(lines) <= 1, 'REMOTE_REF_AMBIGUOUS')
    if not lines:
        return None
    sha, actual = lines[0].split('\t')
    require(actual == ref and re.fullmatch('[0-9a-f]{40}', sha), 'REMOTE_REF_MISMATCH')
    return sha


def publish(directory, output, repo, authorization, transport=None):
    require(re.fullmatch(r'[\w.-]+/[\w.-]+', repo), 'REPO')
    require(authorization.strip(), 'AUTHORIZATION')
    directory, output = Path(directory).resolve(), Path(output).resolve()
    disjoint(directory, output)
    checked = evidence_store.verify(directory)
    identity = read(directory / 'run.json')
    require(read(directory / 'manifest.json')['run'] == identity, 'RUN_MANIFEST_IDENTITY')
    require(identity['repo'] == repo and re.fullmatch('[a-f0-9]{32}', checked['run_id']), 'EVIDENCE_DESTINATION')
    require(identity['run_id'] == directory.name, 'RUN_ID')
    require(not any('.github' in path.relative_to(directory).parts for path in directory.rglob('*')), 'EVIDENCE_WORKFLOW')
    remote = transport or 'https://github.com/' + repo + '.git'
    ref = 'refs/heads/aegis-evidence/' + checked['run_id']
    result = reserve(output, 'aegis-evidence-publication/v1', repo=repo, ref=ref,
                     remote=remote, run_id=checked['run_id'], authorization_ref=authorization,
                     manifest_digest=fingerprint(directory / 'manifest.json'), commit=None,
                     proof_mode='offline-transport' if transport else 'github')
    try:
        require(remote_head(remote, ref) is None, 'REMOTE_REF_EXISTS: reconcile existing run')
        checkout = output / 'checkout'
        checkout.mkdir()
        command(['git', 'init', '--quiet'], checkout)
        command(['git', 'config', 'user.name', 'AEGIS evidence'], checkout)
        command(['git', 'config', 'user.email', 'aegis@localhost'], checkout)
        for path in directory.rglob('*'):
            if path.is_file():
                target = checkout / path.relative_to(directory)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
        # Revalidate the copied bytes; never publish a changed package.
        copied = {p.relative_to(checkout).as_posix(): p.read_bytes() for p in checkout.rglob('*')
                  if p.is_file() and '.git' not in p.relative_to(checkout).parts}
        expected = {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
        require(copied == expected, 'EVIDENCE_COPY_CHANGED')
        evidence_store.verify(directory)
        require(fingerprint(directory / 'manifest.json') == result['manifest_digest'], 'EVIDENCE_CHANGED')
        command(['git', 'add', '--all'], checkout)
        command(['git', 'commit', '--quiet', '-m', 'AEGIS sealed evidence ' + checked['run_id']], checkout)
        result.update(commit=command(['git', 'rev-parse', 'HEAD'], checkout),
                      tree=command(['git', 'rev-parse', 'HEAD^{tree}'], checkout), status='remote_unknown')
        write(output / 'operation.json', result)
        command(['git', 'push', remote, result['commit'] + ':' + ref], checkout)
        require(remote_head(remote, ref) == result['commit'], 'REMOTE_REF_MISMATCH')
        result.update(status='published', url=None if transport else f'https://github.com/{repo}/tree/{result["commit"]}')
    except Exception as error:
        result.update(status='remote_unknown' if result.get('commit') else 'failed', diagnostics=str(error))
        raise
    finally:
        write(output / 'operation.json', result)
    return result


def resume(output):
    result = read(Path(output) / 'operation.json')
    require(result.get('schema') == 'aegis-evidence-publication/v1', 'OPERATION_SCHEMA')
    # Does not write the old record, create refs, fetch into it, or repeat a push.
    try:
        actual = remote_head(result['remote'], result['ref'])
        if actual and actual == result.get('commit'):
            checkout = Path(output) / 'checkout'
            require(command(['git', 'rev-parse', actual + '^{tree}'], checkout) == result['tree'], 'LOCAL_TREE_CHANGED')
            require(len(command(['git', 'rev-list', '--parents', '-n', '1', actual], checkout).split()) == 1, 'EVIDENCE_PARENT')
            return dict(result, status='published', url=None if result.get('proof_mode') == 'offline-transport' else f'https://github.com/{result["repo"]}/tree/{actual}', next_action='Use immutable evidence URL; do not push again.')
        return dict(result, status='remote_unknown', observed_ref=actual,
                    next_action='Inspect original commit/ref and stopped process; absence is not authorization to retry.')
    except Exception as error:
        return dict(result, status='remote_unknown', diagnostics=str(error), next_action='Resolve read failure, then resume original operation.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('publish')
    for key in ('directory', 'output', 'repo', 'authorization-ref'):
        p.add_argument('--' + key, required=True)
    sub.add_parser('resume').add_argument('--output', required=True)
    args = parser.parse_args()
    result = resume(args.output) if args.action == 'resume' else publish(args.directory, args.output, args.repo, args.authorization_ref)
    print(json.dumps(result, indent=2))
    return int(result['status'] != 'published')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error))
