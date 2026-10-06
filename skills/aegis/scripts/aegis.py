#!/usr/bin/env python3
"""GitHub-backed workflow primitives. Python stdlib + authenticated gh only."""
import argparse
import base64
import copy
import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

BRANCH = 'aegis-state'
FILE = 'aegis-state.json'
ROLES = {'new': 'planner', 'design-review': 'reviewer', 'ready': 'developer',
         'code-review': 'reviewer', 'testing': 'qa', 'merge-ready': 'qa'}
EDGES = {'new': {'design-review', 'blocked'},
         'design-review': {'ready', 'new', 'blocked'},
         'ready': {'code-review', 'blocked'},
         'code-review': {'testing', 'ready', 'blocked'},
         'testing': {'merge-ready', 'ready', 'blocked'},
         'merge-ready': {'done', 'testing', 'ready', 'blocked'}}

class WorkflowError(Exception):
    pass

def require(ok, message):
    if not ok:
        raise WorkflowError(message)

def repo_name(value):
    value = value.removeprefix('https://github.com/').rstrip('/').removesuffix('.git')
    require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value)), 'Use OWNER/REPO or a github.com repository URL')
    return value

def gh_api(repo, endpoint='', method='GET', data=None):
    cmd = ['gh', 'api', '--hostname', 'github.com', '-X', method, f'repos/{repo}{endpoint}']
    if data is not None:
        cmd += ['--input', '-']
    try:
        p = subprocess.run(cmd, input=json.dumps(data) if data is not None else None,
                           text=True, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise WorkflowError('REMOTE_UNKNOWN: timeout; inspect remote state before any mutation retry')
    if p.returncode:
        # Do not dump bodies or credentials into diagnostics.
        status = re.search(r'HTTP (\d{3})', p.stderr)
        code = status.group(1) if status else 'unknown'
        raise WorkflowError(f'GITHUB_ERROR HTTP={code} method={method}: inspect auth, permissions, rate limits and current state; no automatic retry; mutation outcome may be unknown')
    return json.loads(p.stdout) if p.stdout.strip() else None

class Store:
    def __init__(self, repo):
        self.repo = repo
    def read(self):
        r = gh_api(self.repo, f'/contents/{FILE}?ref={BRANCH}')
        state = json.loads(base64.b64decode(r['content']))
        require(state['version'] == 1, 'Unsupported state version')
        return state, r['sha']
    def write(self, state, sha, operation):
        raw = json.dumps(state, sort_keys=True, indent=2).encode()
        require(len(raw) < 750000, 'State approaching size limit; archive completed tasks before continuing')
        payload = {'message': f'aegis: {operation}', 'branch': BRANCH,
                   'content': base64.b64encode(raw).decode()}
        if sha:
            payload['sha'] = sha
        gh_api(self.repo, f'/contents/{FILE}', 'PUT', payload)


def new_state():
    return {'version': 1, 'revision': 0, 'tasks': {}, 'qa': None, 'last_operation': None}

def held(task, actor, token, now):
    lease = task.get('lease')
    require(lease and lease['actor'] == actor and lease['token'] == token,
            'NOT_OWNER: actor/token does not own claim')
    require(lease['expires'] > now, 'EXPIRED: stop work; maintainer recovery required')
    return lease

def mutate(source, command, issue, actor, role=None, token=None, ttl=1800,
           target=None, evidence=None, now=None, op=None):
    now = int(time.time()) if now is None else now
    s = copy.deepcopy(source)
    key = str(issue)
    if command == 'register':
        require(key not in s['tasks'], 'Task already registered; inspect current state')
        s['tasks'][key] = {'state': 'new', 'lease': None, 'history': [], 'authors': {}, 'contributors': {}}
    else:
        require(key in s['tasks'], 'Register issue first')
        t = s['tasks'][key]
        if command == 'claim':
            require(ROLES.get(t['state']) == role, 'Role cannot claim this state')
            require(t['lease'] is None, 'BUSY: existing claim, even if expired; recovery is explicit')
            if role == 'reviewer':
                author_role = 'planner' if t['state'] == 'design-review' else 'developer'
                require(actor not in t.get('contributors', {}).get(author_role, []), 'Independent reviewer required')
            if role == 'qa':
                require(s['qa'] is None, 'QA_BUSY: repository-wide integration slot held')
                s['qa'] = {'issue': key, 'token': token}
            if role in ('planner', 'developer'):
                authors = t.setdefault('contributors', {}).setdefault(role, [])
                if actor not in authors:
                    authors.append(actor)
            t['lease'] = {'actor': actor, 'role': role, 'token': token, 'expires': now + ttl}
        elif command == 'heartbeat':
            lease = held(t, actor, token, now)
            lease['expires'] = now + ttl
        elif command in ('finish', 'release'):
            lease = held(t, actor, token, now)
            if command == 'finish':
                require(target in EDGES.get(t['state'], set()), 'Illegal state transition')
                require(isinstance(evidence, dict) and evidence.get('summary') and evidence.get('url'),
                        'Evidence needs summary and durable URL')
                if t['state'] in ('code-review', 'testing', 'merge-ready') or (t['state'] == 'ready' and target == 'code-review'):
                    require(isinstance(evidence.get('pr'), int) and evidence['pr'] > 0 and
                            re.fullmatch(r'[0-9a-f]{40}', evidence.get('head', '')),
                            'Evidence needs positive PR number and full head SHA')
                if target == 'merge-ready':
                    require(evidence.get('result') == 'pass' and
                            re.fullmatch(r'[0-9a-f]{40}', evidence.get('base', '')) and
                            re.fullmatch(r'[0-9a-f]{40}', evidence.get('tested_commit', '')),
                            'QA pass needs exact base and tested integration commit')
                t['history'].append({'from': t['state'], 'to': target, 'actor': actor,
                                     'role': lease['role'], 'at': now, 'evidence': evidence,
                                     'operation': op})
                t['authors'][lease['role']] = actor
                contributors = t.setdefault('contributors', {}).setdefault(lease['role'], [])
                if actor not in contributors:
                    contributors.append(actor)
                t['state'] = target
            if lease['role'] == 'qa':
                require(s['qa'] == {'issue': key, 'token': token}, 'QA ownership mismatch')
                s['qa'] = None
            t['lease'] = None
        else:
            raise WorkflowError('Unknown operation')
    s['revision'] += 1
    s['last_operation'] = op
    return s



def recover(source, issue, actor, reason, target, now=None, op=None):
    """Operator-only after externally confirming all previous work has stopped."""
    s = copy.deepcopy(source)
    t = s['tasks'][str(issue)]
    require(target in ROLES, 'Recovery target must be a working stage')
    require(bool(reason.strip()), 'Recovery reason required')
    require(t['state'] != 'done', 'Completed tasks cannot be reset')
    old = t.get('lease')
    if s['qa'] and s['qa']['issue'] == str(issue):
        s['qa'] = None
    t.setdefault('recovery', []).append({'actor': actor, 'reason': reason,
        'from': t['state'], 'to': target, 'prior_lease': old,
        'at': int(time.time()) if now is None else now, 'operation': op})
    t['lease'] = None
    t['state'] = target
    s['revision'] += 1
    s['last_operation'] = op
    return s


def validate_remote(repo, state, issue, target, evidence):
    t = state['tasks'][str(issue)]
    if t['state'] not in ('code-review', 'testing', 'merge-ready') and not (t['state'] == 'ready' and target == 'code-review'):
        return
    require(isinstance(evidence, dict) and isinstance(evidence.get('pr'), int), 'PR evidence missing')
    pr = gh_api(repo, f"/pulls/{evidence['pr']}")
    require(pr['head']['sha'] == evidence.get('head'), 'STALE_HEAD: PR changed')
    require(pr['base']['repo']['full_name'].lower() == repo.lower(), 'Wrong PR repository')
    if target == 'done':
        require(pr.get('merged') is True, 'PR is not merged; queue admission is not completion')
    else:
        require(pr['state'] == 'open' and not pr['draft'], 'PR must be open and non-draft')
    if target in ('testing', 'merge-ready', 'done'):
        previous = t['history'][-1]['evidence']
        require(previous.get('pr') == evidence['pr'] and previous.get('head') == evidence['head'],
                'Evidence does not match preceding development/review candidate; return to ready')
    if target == 'merge-ready':
        require(pr['base']['sha'] == evidence.get('base'), 'STALE_BASE: repeat integration test')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=repo_name)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    scan = sub.add_parser('scan'); scan.add_argument('--role', choices=sorted(set(ROLES.values())), required=True)
    sub.add_parser('init-remote')
    recovery = sub.add_parser('recover')
    recovery.add_argument('--issue', type=int, required=True)
    recovery.add_argument('--actor', required=True)
    recovery.add_argument('--reason', required=True)
    recovery.add_argument('--to', choices=sorted(ROLES), required=True)
    recovery.add_argument('--confirm-stopped', action='store_true', required=True)
    for command in ('register', 'claim', 'heartbeat', 'finish', 'release'):
        q = sub.add_parser(command)
        q.add_argument('--issue', type=int, required=True)
        q.add_argument('--actor', required=True)
        if command == 'claim':
            q.add_argument('--role', choices=sorted(set(ROLES.values())), required=True)
        if command in ('heartbeat', 'finish', 'release'):
            q.add_argument('--token', required=True)
        if command in ('claim', 'heartbeat'):
            q.add_argument('--ttl', type=int, default=1800)
        if command == 'finish':
            q.add_argument('--to', required=True)
            q.add_argument('--evidence', type=Path, required=True)
    a = p.parse_args(argv)
    store = Store(a.repo)
    if a.command == 'init-remote':
        r = gh_api(a.repo)
        branch = gh_api(a.repo, '/git/ref/heads/' + r['default_branch'])
        gh_api(a.repo, '/git/refs', 'POST', {'ref': 'refs/heads/' + BRANCH, 'sha': branch['object']['sha']})
        store.write(new_state(), None, 'initialize')
        return {'status': 'initialized', 'branch': BRANCH}
    state, sha = store.read()
    if a.command == 'status':
        return state
    if a.command == 'scan':
        return {'revision': state['revision'], 'tasks': [dict(issue=k, **v) for k, v in state['tasks'].items()
                if ROLES.get(v['state']) == a.role and v['lease'] is None],
                'qa_busy': state['qa'] is not None}
    require(a.issue > 0, 'Issue must be positive')
    require(bool(re.fullmatch(r'[A-Za-z0-9_.:@-]{1,100}', a.actor)), 'Invalid actor ID')
    ttl = getattr(a, 'ttl', 1800)
    require(60 <= ttl <= 7200, 'TTL must be 60..7200 seconds')
    issue = gh_api(a.repo, f'/issues/{a.issue}')
    closed_reconciliation = (a.command in ('release', 'heartbeat', 'recover') or
        (a.command == 'finish' and a.to == 'done') or
        (a.command == 'claim' and state['tasks'].get(str(a.issue), {}).get('state') == 'merge-ready'))
    require('pull_request' not in issue and (issue['state'] == 'open' or closed_reconciliation),
            'Expected open issue, except finalization/release of an existing task')
    token = uuid.uuid4().hex if a.command == 'claim' else getattr(a, 'token', None)
    op = uuid.uuid4().hex
    evidence = json.loads(a.evidence.read_text()) if a.command == 'finish' else None
    if a.command == 'recover':
        updated = recover(state, a.issue, a.actor, a.reason, a.to, op=op)
    else:
        updated = mutate(state, a.command, a.issue, a.actor, getattr(a, 'role', None), token, ttl,
                         getattr(a, 'to', None), evidence, op=op)
    if a.command == 'finish':
        validate_remote(a.repo, state, a.issue, a.to, evidence)
    # Persist intent ID before remote mutation so timeout reconciliation is possible.
    print(json.dumps({'operation': op, 'phase': 'attempt', 'token': token}), file=sys.stderr, flush=True)
    store.write(updated, sha, op)
    return {'status': 'ok', 'operation': op, 'token': token, 'task': updated['tasks'][str(a.issue)]}

if __name__ == '__main__':
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (WorkflowError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc), 'retry': False}), file=sys.stderr)
        sys.exit(1)
