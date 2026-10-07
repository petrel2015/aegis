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
from urllib.parse import quote
from pathlib import Path
import policy

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

class GitHubError(WorkflowError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


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
        raise GitHubError(f'GITHUB_ERROR HTTP={code} method={method}: inspect auth, permissions, rate limits and current state; no automatic retry; mutation outcome may be unknown', int(code) if code.isdigit() else None)
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
                                     'role': lease['role'], 'claim_token': token, 'at': now, 'evidence': evidence,
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
    if command in ('register', 'finish'):
        before = source['tasks'].get(key, {}).get('state', 'unregistered')
        enqueue(s['tasks'][key], before, actor, op, now, evidence)
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
    enqueue(t, source['tasks'][str(issue)]['state'], actor, op,
            int(time.time()) if now is None else now, {'summary': reason}, kind='recovery')
    s['revision'] += 1
    s['last_operation'] = op
    return s



LABEL_STATES = set(ROLES) | {'blocked', 'done'}
MANAGED_LABELS = {'aegis:' + state for state in LABEL_STATES}


def enqueue(task, before, actor, operation, at, evidence=None, kind='transition'):
    task.setdefault('issue_events', []).append({
        'id': operation or uuid.uuid4().hex, 'from': before, 'to': task['state'],
        'actor': actor, 'at': at, 'kind': kind, 'evidence': evidence or
        {'summary': 'Task registered for planning'}, 'delivery': 'pending'})


def pages(repo, path):
    for page in range(1, 1001):
        data = gh_api(repo, f'{path}?per_page=100&page={page}')
        require(isinstance(data, list), 'Invalid paginated response')
        yield from data
        if len(data) < 100:
            return
    raise WorkflowError('Pagination limit reached; cannot prove absence')


def event_body(issue, event):
    # Quote user-provided lines so they cannot break the marker or impersonate metadata.
    def quoted(value):
        return '\n'.join('> ' + line for line in str(value).splitlines())
    ev = event['evidence']
    body = (f"<!-- aegis-event:{issue}:{event['id']} -->\n"
            f"### AEGIS: {event['from']} → {event['to']}\n\n"
            f"Operation: `{event['id']}` · Type: `{event['kind']}` · Recorded: {event['at']}\n\n"
            f"Actor:\n{quoted(event['actor'])}\n\n"
            f"Reason / result:\n{quoted(ev.get('summary', 'No summary recorded'))}\n")
    if ev.get('url'):
        body += f"\nEvidence:\n{quoted(ev['url'])}\n"
    if event['to'] == 'blocked':
        body += '\nMaintainer action required: resolve the blocker and use audited recovery.\n'
    return body + '\nHistorical event; current state is authoritative in aegis-state.\n'


def change_delivery(store, issue, event_id, expected, target, url=None):
    state, sha = store.read()
    events = state['tasks'][str(issue)]['issue_events']
    event = next(e for e in events if e['id'] == event_id)
    require(event['delivery'] == expected, 'SYNC_BUSY: event changed; reread before retry')
    event['delivery'] = target
    if url:
        event['comment_url'] = url
    state['revision'] += 1
    # Keep last_operation for the business mutation; projection has separate commit IDs.
    store.write(state, sha, 'issue-sync-' + uuid.uuid4().hex)


def sync_labels(store, issue):
    repo = store.repo
    state, _ = store.read()
    desired_state = state['tasks'][str(issue)]['state']
    require(desired_state in LABEL_STATES, 'Unknown workflow state')
    desired = 'aegis:' + desired_state
    endpoint = '/labels/' + quote(desired, safe='')
    try:
        gh_api(repo, endpoint)
    except GitHubError as exc:
        if exc.status != 404:
            raise
        try:
            gh_api(repo, '/labels', 'POST', {'name': desired,
                   'color': 'B02418' if desired_state == 'blocked' else '56338A',
                   'description': 'AEGIS workflow state (display only)'})
        except GitHubError as create_error:
            if create_error.status != 422:
                raise
            # Another agent may have created it. A failed read remains a sync failure.
            gh_api(repo, endpoint)
    names = {x['name'] for x in pages(repo, f'/issues/{issue}/labels')}
    def current():
        require(store.read()[0]['tasks'][str(issue)]['state'] == desired_state,
                'SYNC_STALE: state changed during label synchronization; rerun sync')
    if desired not in names:
        current()
        gh_api(repo, f'/issues/{issue}/labels', 'POST', {'labels': [desired]})
    for name in sorted((names & MANAGED_LABELS) - {desired}):
        current()
        try:
            gh_api(repo, f'/issues/{issue}/labels/' + quote(name, safe=''), 'DELETE')
        except GitHubError as exc:
            if exc.status != 404:
                raise
    current()
    actual = {x['name'] for x in pages(repo, f'/issues/{issue}/labels')}
    require(actual & MANAGED_LABELS == {desired}, 'SYNC_STALE: labels changed; rerun sync')
    return desired


def sync_issue(store, issue):
    """Best-effort projection after authoritative state commits; never replay business work."""
    repo = store.repo
    try:
        state, sha = store.read()
        require(str(issue) in state['tasks'], 'Task is not registered')
        task = state['tasks'][str(issue)]
        if 'issue_events' not in task:
            # Existing installations get one current-state snapshot, not fabricated history.
            sources = task.get('history', []) + task.get('recovery', [])
            last = max(sources, key=lambda e: e.get('at', 0), default={})
            evidence = last.get('evidence') or {'summary': last.get('reason', 'Existing task state snapshot')}
            enqueue(task, task['state'], last.get('actor', 'migration'), uuid.uuid4().hex,
                    int(time.time()), evidence, kind='snapshot')
            state['revision'] += 1
            store.write(state, sha, 'issue-sync-snapshot-' + uuid.uuid4().hex)
        label = sync_labels(store, issue)
        events = store.read()[0]['tasks'][str(issue)].get('issue_events', [])
        pending = [e for e in events if e['delivery'] != 'sent']
        if pending:
            comments = list(pages(repo, f'/issues/{issue}/comments'))
            for event in pending[:20]:
                body = event_body(issue, event)
                match = next((c for c in comments if c.get('body') == body), None)
                if match:
                    change_delivery(store, issue, event['id'], event['delivery'], 'sent', match['html_url'])
                    continue
                require(event['delivery'] == 'pending',
                        f"REMOTE_UNKNOWN: comment {event['id']} was attempted; absent from listing is not proof of failure; do not repost")
                # CAS reserves the one and only automatic POST attempt across all workers.
                change_delivery(store, issue, event['id'], 'pending', 'sending')
                posted = gh_api(repo, f'/issues/{issue}/comments', 'POST', {'body': body})
                change_delivery(store, issue, event['id'], 'sending', 'sent', posted['html_url'])
        remaining = [e['id'] for e in store.read()[0]['tasks'][str(issue)].get('issue_events', [])
                     if e['delivery'] != 'sent']
        return {'status': 'pending' if remaining else 'synced', 'label': label,
                'pending_events': remaining, 'resume': f'python3 aegis.py --repo {repo} sync --issue {issue}'}
    except (WorkflowError, OSError, ValueError, KeyError, StopIteration) as exc:
        return {'status': 'pending', 'error': str(exc),
                'resume': f'python3 aegis.py --repo {repo} sync --issue {issue}'}


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



def intake_candidates(store, state, sha, actor, project_policy):
    require(bool(re.fullmatch(r'[A-Za-z0-9_.:@-]{1,100}', actor)), 'Invalid actor ID')
    candidates, rejected = [], []
    for issue in pages(store.repo, '/issues'):
        if 'pull_request' in issue or str(issue['number']) in state['tasks']:
            continue
        try:
            requirements = policy.intake_issue(issue, project_policy)
            candidates.append((requirements['priority'], issue['number'], requirements))
        except policy.PolicyError as exc:
            rejected.append({'issue': issue['number'], 'reason': str(exc)})
    registered = []
    for _, number, requirements in sorted(candidates)[:project_policy['max_issues_per_run']]:
        operation = uuid.uuid4().hex
        updated = mutate(state, 'register', number, actor, op=operation)
        updated['tasks'][str(number)]['requirements'] = requirements
        store.write(updated, sha, operation)
        registered.append({'issue': number, 'operation': operation, 'sync': sync_issue(store, number)})
        state, sha = store.read()
    return {'status': 'ok', 'registered': registered, 'rejected': rejected}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', required=True, type=repo_name)
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    merge = sub.add_parser('queue-merge', help='Verify server gates and enqueue an owned QA candidate once')
    merge.add_argument('--issue', type=int, required=True)
    merge.add_argument('--actor', required=True)
    merge.add_argument('--token', required=True)
    sub.add_parser('preflight', help='Validate trusted default-branch project policy')
    intake = sub.add_parser('intake', help='Discover, validate and register eligible Issues')
    intake.add_argument('--actor', required=True)
    sync = sub.add_parser('sync', help='Reconcile labels and event comments without changing workflow stage')
    sync.add_argument('--issue', type=int, required=True)
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
    if a.command == 'queue-merge':
        import merge_gate
        return merge_gate.enqueue(store, a.actor, a.token, a.issue, gh_api, held)
    if a.command == 'init-remote':
        r = gh_api(a.repo)
        branch = gh_api(a.repo, '/git/ref/heads/' + r['default_branch'])
        gh_api(a.repo, '/git/refs', 'POST', {'ref': 'refs/heads/' + BRANCH, 'sha': branch['object']['sha']})
        store.write(new_state(), None, 'initialize')
        return {'status': 'initialized', 'branch': BRANCH}
    project_policy = None
    if a.command not in ('status', 'scan', 'sync', 'heartbeat', 'release'):
        project_policy = policy.load_policy(a.repo, gh_api)
    if a.command == 'preflight':
        return {'status': 'ok', 'policy': project_policy, 'diagnostics': []}
    state, sha = store.read()
    if a.command == 'intake':
        return intake_candidates(store, state, sha, a.actor, project_policy)
    if a.command == 'sync':
        require(a.issue > 0, 'Issue must be positive')
        return {'status': 'ok', 'issue': a.issue, 'sync': sync_issue(store, a.issue)}
    if a.command == 'status':
        return state
    if a.command == 'scan':
        return {'revision': state['revision'], 'tasks': [dict(issue=k, **v) for k, v in sorted(state['tasks'].items(), key=lambda item: (item[1].get('requirements', {}).get('priority', 2), int(item[0])))
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
    requirements = None
    if a.command == 'register':
        requirements = policy.intake_issue(issue, project_policy)
    if a.command == 'claim':
        task = state['tasks'].get(str(a.issue), {})
        policy.validate_claim(state, task, project_policy)
        require(task['requirements']['source_body'] == (issue.get('body') or ''), 'ISSUE_CHANGED: requirements changed after registration; maintainer review required')
    if a.command == 'finish' and a.to != 'blocked':
        current_task = state['tasks'][str(a.issue)]
        require(current_task.get('requirements', {}).get('source_body') == (issue.get('body') or ''), 'ISSUE_CHANGED: immutable requirement snapshot differs')
    token = uuid.uuid4().hex if a.command == 'claim' else getattr(a, 'token', None)
    op = uuid.uuid4().hex
    evidence = json.loads(a.evidence.read_text()) if a.command == 'finish' else None
    if a.command == 'recover':
        updated = recover(state, a.issue, a.actor, a.reason, a.to, op=op)
    else:
        updated = mutate(state, a.command, a.issue, a.actor, getattr(a, 'role', None), token, ttl,
                         getattr(a, 'to', None), evidence, op=op)
    if requirements:
        updated['tasks'][str(a.issue)]['requirements'] = requirements
    if a.command == 'finish':
        policy.evidence_gate(state['tasks'][str(a.issue)], a.to, evidence, project_policy)
        policy.remote_gate(a.repo, state['tasks'][str(a.issue)], a.to, evidence, project_policy, gh_api)
        validate_remote(a.repo, state, a.issue, a.to, evidence)
    # Persist intent ID before remote mutation so timeout reconciliation is possible.
    print(json.dumps({'operation': op, 'phase': 'attempt', 'token': token}), file=sys.stderr, flush=True)
    store.write(updated, sha, op)
    result = {'status': 'ok', 'operation': op, 'token': token, 'task': updated['tasks'][str(a.issue)]}
    if a.command in ('register', 'finish', 'recover'):
        result['sync'] = sync_issue(store, a.issue)
    return result

if __name__ == '__main__':
    try:
        print(json.dumps(main(), ensure_ascii=False, indent=2))
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc), 'retry': False}), file=sys.stderr)
        sys.exit(1)
