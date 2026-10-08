#!/usr/bin/env python3
"""Prepare guarded static artifacts, publish Git artifacts, and verify public files.

No inferred deployment authorization; each command retains its own result directory.
"""
import argparse
import fnmatch
import hashlib
import http.client
from html.parser import HTMLParser
import json
import os
import signal
from pathlib import Path
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import zipfile

PROTECTED = ('CNAME', '.nojekyll', 'ATTRIBUTION*', 'LICENSE*', 'COPYING*')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inventory(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'ARTIFACT_ROOT: real directory required')
    files = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '.git' in relative.parts:
            continue
        require(not path.is_symlink(), f'ARTIFACT_SYMLINK: {relative}')
        if not path.is_file():
            continue
        require(not any(p in ('.github', 'node_modules', '.aegis-local', '.ssh') or p.startswith('.env') for p in relative.parts), f'ARTIFACT_PRIVATE: {relative}')
        files[relative.as_posix()] = path.read_bytes()
    return files


def valid_site(site):
    parts = urllib.parse.urlsplit(site)
    require(parts.scheme == 'https' and parts.netloc and not parts.username and not parts.password and not parts.query and not parts.fragment, 'SITE_URL: exact HTTPS base required')
    require(site.endswith('/'), 'SITE_URL: trailing slash required')
    return site


def validate_base(index, site):
    origin = urllib.parse.urlsplit(site)
    class Resources(HTMLParser):
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'base' and attrs.get('href') is not None:
                require(urllib.parse.urljoin(site, attrs['href']) == site, 'BUILD_BASE_PATH: HTML base must equal authorized site base')
            ref = attrs.get('src') if tag in ('script', 'img', 'source') else attrs.get('href') if tag == 'link' else None
            if not ref or ref.startswith(('data:', 'blob:')):
                return
            decoded = urllib.parse.unquote(ref)
            require('\\' not in decoded, 'BUILD_BASE_PATH: backslash resource path')
            raw_path = urllib.parse.urlsplit(ref).path
            require(not any(urllib.parse.unquote(part) in ('.', '..') and urllib.parse.unquote(part) != part for part in raw_path.split('/')), 'BUILD_BASE_PATH: encoded dot segment')
            resolved = urllib.parse.urlsplit(urllib.parse.urljoin(site, ref))
            if resolved.netloc == origin.netloc:
                require(resolved.scheme == origin.scheme and resolved.path.startswith(origin.path),
                        'BUILD_BASE_PATH: local resource escapes authorized site base: ' + ref)
    Resources().feed(index.decode('utf-8'))


def prepare(build, previous, output, source_sha, site, allow_remove=(), protected=()):
    require(re.fullmatch('[0-9a-f]{40}', source_sha), 'SOURCE_SHA: full commit required')
    valid_site(site)
    output = Path(output)
    require(not output.exists(), 'RUN_EXISTS: use a fresh output directory')
    build, previous = Path(build), Path(previous)
    require(not output.resolve().is_relative_to(build.resolve()) and not output.resolve().is_relative_to(previous.resolve()), 'OUTPUT_OVERLAP')
    current, old = inventory(build), inventory(previous)
    require('index.html' in current, 'ARTIFACT_ENTRY: index.html required')
    validate_base(current['index.html'], site)
    if 'build.json' in current:
        metadata = json.loads(current['build.json'])
        require(metadata.get('sourceCommit') == source_sha, 'BUILD_VERSION: existing metadata disagrees with source')
    else:
        current['build.json'] = (json.dumps({'sourceCommit': source_sha, 'mode': 'pages'}, indent=2) + '\n').encode()
    retained = []
    patterns = (*PROTECTED, *protected)
    for name, data in old.items():
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns):
            if name in current:
                require(current[name] == data, f'PROTECTED_CHANGED: {name}; review separately before release')
            else:
                current[name] = data
                retained.append(name)
    removed = sorted(set(old) - set(current))
    unapproved = [name for name in removed if name not in allow_remove]
    require(not unapproved, 'REMOVAL_REVIEW: ' + ', '.join(unapproved))
    output.mkdir(parents=True)
    stage = output / 'artifact'
    stage.mkdir()
    for name, data in current.items():
        path = stage / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    with zipfile.ZipFile(output / 'artifact.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(current):
            archive.write(stage / name, name)
    manifest = {'schema': 'aegis-artifact/v1', 'source_sha': source_sha, 'site_url': site,
                'files': {name: digest(data) for name, data in sorted(current.items())},
                'artifact_digest': 'sha256:' + digest((output / 'artifact.zip').read_bytes()),
                'diff': {'added': sorted(set(current) - set(old)), 'removed': removed,
                         'changed': sorted(n for n in set(current) & set(old) if current[n] != old[n]),
                         'retained': retained, 'approved_removals': sorted(allow_remove)},
                'protected': list(patterns), 'previous_files': {name: digest(data) for name, data in sorted(old.items())}}
    (output / 'artifact.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def load_artifact(directory):
    directory = Path(directory)
    require(not directory.is_symlink(), 'ARTIFACT_SYMLINK')
    manifest = json.loads((directory / 'artifact.json').read_text())
    require(manifest.get('schema') == 'aegis-artifact/v1', 'ARTIFACT_SCHEMA')
    actual = inventory(directory / 'artifact')
    require({n: digest(b) for n, b in actual.items()} == manifest['files'], 'ARTIFACT_CHANGED')
    require('sha256:' + digest((directory / 'artifact.zip').read_bytes()) == manifest['artifact_digest'], 'ARCHIVE_CHANGED')
    with zipfile.ZipFile(directory / 'artifact.zip') as archive:
        require(set(archive.namelist()) == set(actual) and len(archive.namelist()) == len(actual), 'ARCHIVE_FILES')
        require(all(archive.read(n) == data for n, data in actual.items()), 'ARCHIVE_CHANGED')
    valid_site(manifest['site_url'])
    validate_base(actual['index.html'], manifest['site_url'])
    return manifest, actual


def command(argv, cwd=None, timeout=60):
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    require(result.returncode == 0, 'COMMAND_FAILED: ' + argv[0] + ' exit=' + str(result.returncode))
    return result.stdout.strip()


def publish(directory, checkout, repo, expected_base, authorization):
    require(authorization.strip(), 'AUTHORIZATION: actual user reference required')
    require(re.fullmatch(r'[\w.-]+/[\w.-]+', repo), 'REPO: OWNER/REPO required')
    require(re.fullmatch('[0-9a-f]{40}', expected_base), 'BASE_SHA')
    manifest, files = load_artifact(directory)
    require(not (Path(directory) / 'publish.json').exists(), 'PUBLISH_EXISTS: reconcile original attempt before any mutation')
    checkout = Path(checkout)
    require(not checkout.resolve().is_relative_to(Path(directory).resolve()) and not Path(directory).resolve().is_relative_to(checkout.resolve()), 'CHECKOUT_OVERLAP')
    require(command(['git', 'status', '--porcelain'], checkout) == '', 'CHECKOUT_DIRTY')
    origin = command(['git', 'remote', 'get-url', 'origin'], checkout)
    require(origin.rstrip('/').removesuffix('.git') in ('https://github.com/' + repo, 'git@github.com:' + repo), 'DESTINATION_MISMATCH')
    branch = command(['git', 'branch', '--show-current'], checkout)
    require(branch and branch != 'aegis-state', 'ARTIFACT_BRANCH')
    require(command(['git', 'rev-parse', 'HEAD'], checkout) == expected_base, 'LOCAL_BASE_CHANGED')
    remote = json.loads(command(['gh', 'api', f'repos/{repo}/git/ref/heads/{branch}']))
    require(remote['object']['sha'] == expected_base, 'REMOTE_BASE_CHANGED')
    old = inventory(checkout)
    require({n: digest(b) for n, b in old.items()} == manifest['previous_files'], 'PREVIOUS_ARTIFACT_CHANGED: prepare against exact checkout before publication')
    for name, data in old.items():
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in manifest['protected']):
            require(files.get(name) == data, 'PROTECTED_CHANGED: ' + name)
    lock_path = Path(command(['git', 'rev-parse', '--git-path', 'aegis-release.lock'], checkout))
    if not lock_path.is_absolute():
        lock_path = checkout / lock_path
    # Atomic local exclusion covers distinct run directories sharing this checkout.
    # A failed/unknown attempt retains the lock for explicit reconciliation.
    with lock_path.open('x') as lock:
        lock.write(str(Path(directory).resolve()))
    try:
        require(command(['git', 'status', '--porcelain'], checkout) == '', 'CHECKOUT_DIRTY')
        require(command(['git', 'rev-parse', 'HEAD'], checkout) == expected_base, 'LOCAL_BASE_CHANGED')
        require(command(['git', 'branch', '--show-current'], checkout) == branch, 'ARTIFACT_BRANCH_CHANGED')
        current_remote = json.loads(command(['gh', 'api', f'repos/{repo}/git/ref/heads/{branch}']))
        require(current_remote['object']['sha'] == expected_base, 'REMOTE_BASE_CHANGED')
        require({n: digest(b) for n, b in inventory(checkout).items()} == manifest['previous_files'], 'PREVIOUS_ARTIFACT_CHANGED')
    except Exception:
        lock_path.unlink()
        raise
    receipt_path = Path(directory) / 'publish.json'
    result = {'status': 'remote_unknown', 'repo': repo, 'branch': branch,
              'artifact_commit': None, 'previous_commit': expected_base,
              'authorization_ref': authorization, 'source_sha': manifest['source_sha'],
              'diagnostics': 'Local preparation reserved; reconcile checkout and original remote before retry.'}
    with receipt_path.open('x') as report:
        json.dump(result, report, indent=2)
    # Only tracked/untracked publishable file paths from a clean checkout are touched.
    for name in set(old) - set(files):
        (checkout / name).unlink()
    for name, data in files.items():
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    command(['git', 'add', '--all'], checkout)
    if command(['git', 'diff', '--cached', '--name-only'], checkout):
        command(['git', 'commit', '-m', 'Publish static artifact from ' + manifest['source_sha']], checkout)
    sha = command(['git', 'rev-parse', 'HEAD'], checkout)
    result.update(artifact_commit=sha, diagnostics='Inspect original commit/ref before retrying a push.')
    receipt_path.write_text(json.dumps(result, indent=2) + '\n')
    # Push once: non-fast-forward rejection and unknown outcomes never automatically retry.
    command(['git', 'push', 'origin', f'{sha}:refs/heads/{branch}'], checkout)
    result.update(status='pending', diagnostics='Push succeeded; deployment success and public proof still required.')
    receipt_path.write_text(json.dumps(result, indent=2) + '\n')
    lock_path.unlink()
    return result


def fetch(url):
    request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=30) as response:
        require(urllib.parse.urlsplit(response.url).netloc == urllib.parse.urlsplit(url).netloc, 'VERIFY_REDIRECT: cross-origin response')
        return response.read()


def fetch_curl(url):
    # Optional explicit transport for hosts whose urllib/proxy streams truncate.
    # No redirect following and no automatic retries; retain original attempt.
    result = subprocess.run(['curl', '--fail', '--silent', '--show-error',
                             '--connect-timeout', '10', '--max-time', '30', url],
                            capture_output=True, timeout=35)
    require(result.returncode == 0, 'PUBLIC_TRANSPORT: curl exit=' + str(result.returncode))
    return result.stdout


def verify(directory, output, downloader=fetch):
    manifest, files = load_artifact(directory)
    output = Path(output)
    require(not output.exists(), 'RUN_EXISTS: verification retries need fresh output')
    require(not output.resolve().is_relative_to(Path(directory).resolve()), 'OUTPUT_OVERLAP: verification must not modify retained artifact')
    output.mkdir(parents=True)
    observed = {}
    result = {'status': 'remote_unknown', 'source_sha': manifest['source_sha'],
              'site_url': manifest['site_url'], 'files': observed, 'exclusions': [],
              'transport': 'curl' if downloader is fetch_curl else 'urllib' if downloader is fetch else 'injected'}
    try:
        for name, data in files.items():
            url = manifest['site_url'] + urllib.parse.quote(name, safe='/') + '?aegis=' + manifest['artifact_digest'][7:19]
            live = downloader(url)
            require(live == data, 'PUBLIC_FILE_MISMATCH: ' + name)
            observed[name] = digest(live)
        require(json.loads(files['build.json'])['sourceCommit'] == manifest['source_sha'], 'PUBLIC_VERSION_MISMATCH')
        result.update(status='files_verified', observed_artifact_digest=manifest['artifact_digest'],
                      observed_source_sha=manifest['source_sha'], proof='All public files match retained archive; browser smoke and deployment outcome separately required.')
    except Exception as error:
        result['diagnostics'] = str(error)
        raise
    finally:
        (output / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def smoke(argv, output, target, timeout=180):
    valid_site(target)
    require(isinstance(argv, list) and argv and all(isinstance(a, str) and a for a in argv), 'SMOKE_ARGV')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = {'status': 'unverified', 'target': target, 'argv': argv}
    process = None
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=(os.name != 'nt'))
        stdout, stderr = process.communicate(timeout=timeout)
        (output / 'stdout.log').write_bytes(stdout)
        (output / 'stderr.log').write_bytes(stderr)
        result.update(exit_code=process.returncode, status='pass' if process.returncode == 0 else 'fail',
                      proof='Configured project smoke command exit; inspect browser observations before declaring acceptance.')
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=15)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        stdout, stderr = process.communicate(timeout=15)
        (output / 'stdout.log').write_bytes(stdout)
        (output / 'stderr.log').write_bytes(stderr)
        result.update(status='remote_unknown', diagnostics='SMOKE_TIMEOUT: local process group stopped; inspect external outcome before retry')
    finally:
        (output / 'smoke.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    p = sub.add_parser('prepare')
    for arg in ('build', 'previous', 'output', 'source-sha', 'site'):
        p.add_argument('--' + arg, required=True)
    p.add_argument('--allow-remove', action='append', default=[])
    p.add_argument('--protect', action='append', default=[])
    p = sub.add_parser('publish')
    for arg in ('artifact', 'checkout', 'repo', 'expected-base', 'authorization-ref'):
        p.add_argument('--' + arg, required=True)
    p = sub.add_parser('verify')
    p.add_argument('--artifact', required=True); p.add_argument('--output', required=True)
    p.add_argument('--transport', choices=('urllib', 'curl'), default='urllib')
    p = sub.add_parser('smoke')
    p.add_argument('--argv-json', required=True); p.add_argument('--output', required=True)
    p.add_argument('--target', required=True); p.add_argument('--timeout', type=int, default=180)
    a = parser.parse_args()
    if a.operation == 'prepare':
        result = prepare(a.build, a.previous, a.output, a.source_sha, a.site, a.allow_remove, a.protect)
    elif a.operation == 'publish':
        result = publish(a.artifact, a.checkout, a.repo, a.expected_base, a.authorization_ref)
    elif a.operation == 'verify':
        result = verify(a.artifact, a.output, fetch_curl if a.transport == 'curl' else fetch)
    else:
        result = smoke(json.loads(Path(a.argv_json).read_text()), a.output, a.target, a.timeout)
    print(json.dumps(result, indent=2))
    return 1 if result.get('status') in ('fail', 'remote_unknown') else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, http.client.HTTPException) as error:
        raise SystemExit(str(error))
