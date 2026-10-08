"""Isolate coordination commits from inherited product workflows using GitHub Git APIs.

No retry, force push, local Git checkout, or state/history rewrite. Callers authorize
an exact repository; mutation uncertainty must be reconciled before another attempt.
"""
import base64
import json
import re
from urllib.parse import quote

BRANCH = 'aegis-state'
FILE = 'aegis-state.json'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ref_endpoint():
    return '/git/ref/heads/' + quote(BRANCH, safe='')


def initialize(repo, api, state):
    # Confirm a real, nonempty repository and never replace an existing state ref.
    metadata = api(repo)
    api(repo, '/git/ref/heads/' + quote(metadata['default_branch'], safe=''))
    try:
        api(repo, ref_endpoint())
    except Exception as exc:
        if getattr(exc, 'status', None) != 404:
            raise
    else:
        raise ValueError('STATE_EXISTS: inspect existing branch; initialization never resets it')
    raw = json.dumps(state, sort_keys=True, indent=2)
    blob = api(repo, '/git/blobs', 'POST', {'content': raw, 'encoding': 'utf-8'})
    tree = api(repo, '/git/trees', 'POST', {'tree': [
        {'path': FILE, 'mode': '100644', 'type': 'blob', 'sha': blob['sha']}]})
    commit = api(repo, '/git/commits', 'POST', {
        'message': 'aegis: initialize isolated coordination state',
        'tree': tree['sha'], 'parents': []})
    api(repo, '/git/refs', 'POST', {'ref': 'refs/heads/' + BRANCH, 'sha': commit['sha']})
    return {'status': 'initialized', 'branch': BRANCH, 'head': commit['sha'],
            'isolated_tree': True}


def inspect(repo, api):
    head = api(repo, ref_endpoint())['object']['sha']
    commit = api(repo, '/git/commits/' + head)
    tree_sha = commit['tree']['sha']
    tree = api(repo, '/git/trees/' + tree_sha + '?recursive=1')
    require(not tree.get('truncated'), 'TREE_TRUNCATED: cannot safely plan migration')
    entries = tree['tree']
    state_entries = [e for e in entries if e['path'] == FILE and e['type'] == 'blob']
    require(len(state_entries) == 1, 'STATE_MISSING: expected one coordination state blob')
    blob_sha = state_entries[0]['sha']
    blob = api(repo, '/git/blobs/' + blob_sha)
    require(blob.get('encoding') == 'base64', 'STATE_ENCODING: unsupported blob encoding')
    state = json.loads(base64.b64decode(blob['content']))
    require(state.get('version') == 1 and isinstance(state.get('tasks'), dict),
            'STATE_FORMAT: unsupported coordination state')
    workflows = sorted(e['path'] for e in entries
                       if e['type'] == 'blob' and e['path'].startswith('.github/workflows/'))
    return head, tree_sha, blob_sha, state, workflows, entries


def idle(state):
    require(state.get('qa') is None, 'QA_BUSY: release integration slot before migration')
    for key, task in state['tasks'].items():
        require(task.get('lease') is None, 'CLAIM_BUSY: stop and release task ' + key)
        require(not task.get('merge_request') or task.get('state') == 'done',
                'MERGE_PENDING: resolve queue request for task ' + key)


def isolate(repo, api, apply=False, expected_head=None, confirm_stopped=False):
    head, tree_sha, state_blob, state, workflows, entries = inspect(repo, api)
    report = {'status': 'plan', 'branch': BRANCH, 'head': head,
              'state_blob': state_blob, 'state_revision': state.get('revision'),
              'remove': workflows, 'preserves_state_and_history': True}
    if not apply:
        return report
    require(confirm_stopped, 'CONFIRM_STOPPED: stop all coordination writers first')
    require(isinstance(expected_head, str) and re.fullmatch(r'[0-9a-f]{40}', expected_head),
            'EXPECTED_HEAD: use the full SHA from the reviewed migration plan')
    require(head == expected_head, 'HEAD_STALE: inspect and review a fresh plan')
    idle(state)
    if not workflows:
        return dict(report, status='already_isolated')
    require(any(e['path'] == '.github/workflows' and e['type'] == 'tree' for e in entries),
            'WORKFLOW_TREE: expected workflow directory')
    tree = api(repo, '/git/trees', 'POST', {'base_tree': tree_sha, 'tree': [
        {'path': '.github/workflows', 'mode': '040000', 'type': 'tree', 'sha': None}]})
    # The parent is the reviewed head. A concurrent contents/state write creates a
    # sibling, so force:false refuses to replace it (rather than losing its state).
    commit = api(repo, '/git/commits', 'POST', {
        'message': 'aegis: remove inherited product CI from coordination branch',
        'tree': tree['sha'], 'parents': [head]})
    api(repo, '/git/refs/heads/' + quote(BRANCH, safe=''), 'PATCH',
        {'sha': commit['sha'], 'force': False})
    observed = inspect(repo, api)
    require(observed[2] == state_blob and not observed[4],
            'POSTCHECK_CHANGED: inspect branch before continuing; no automatic retry')
    return dict(report, status='isolated', migration_commit=commit['sha'],
                observed_head=observed[0])
