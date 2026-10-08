import base64
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/aegis/scripts'))
import aegis
import state_branch


class FakeGit:
    def __init__(self, exists=True):
        self.calls = []
        self.head = 'a' * 40 if exists else None
        self.state = aegis.new_state()
        self.state['tasks']['1'] = {'state': 'done', 'lease': None,
                                   'history': [{'evidence': {'summary': 'kept'}}]}
        self.entries = [
            {'path': 'aegis-state.json', 'type': 'blob', 'mode': '100644', 'sha': 'b' * 40},
            {'path': '.github/workflows', 'type': 'tree', 'mode': '040000', 'sha': 'c' * 40},
            {'path': '.github/workflows/test.yml', 'type': 'blob', 'mode': '100644', 'sha': 'd' * 40},
            {'path': 'src/app.js', 'type': 'blob', 'mode': '100644', 'sha': 'e' * 40}]
        self.truncated = False
        self.race = False
        self.timeout = False
        self.new_entries = None
        self.new_commit = None

    def __call__(self, repo, endpoint='', method='GET', data=None):
        self.calls.append((endpoint, method, copy.deepcopy(data)))
        if endpoint == '':
            return {'default_branch': 'main'}
        if endpoint == '/git/ref/heads/main':
            return {'object': {'sha': 'f' * 40}}
        if endpoint == '/git/ref/heads/aegis-state':
            if self.head is None:
                raise aegis.GitHubError('not found', 404)
            return {'object': {'sha': self.head}}
        if endpoint.startswith('/git/commits/'):
            return {'tree': {'sha': '1' * 40}}
        if endpoint.startswith('/git/trees/'):
            return {'tree': copy.deepcopy(self.entries), 'truncated': self.truncated}
        if endpoint.startswith('/git/blobs/'):
            return {'encoding': 'base64', 'content': base64.b64encode(json.dumps(self.state).encode()).decode()}
        if endpoint == '/git/blobs' and method == 'POST':
            return {'sha': '2' * 40}
        if endpoint == '/git/trees' and method == 'POST':
            if 'base_tree' in data:
                self.new_entries = [e for e in self.entries if not e['path'].startswith('.github/workflows')]
            else:
                self.new_entries = data['tree']
            return {'sha': '3' * 40}
        if endpoint == '/git/commits' and method == 'POST':
            self.new_commit = copy.deepcopy(data)
            return {'sha': '4' * 40}
        if endpoint == '/git/refs' and method == 'POST':
            if self.head is not None:
                raise aegis.GitHubError('already exists', 422)
            self.head = data['sha']
            self.entries = self.new_entries
            return {'object': {'sha': self.head}}
        if endpoint == '/git/refs/heads/aegis-state' and method == 'PATCH':
            if self.timeout:
                raise aegis.WorkflowError('REMOTE_UNKNOWN')
            if self.race:
                self.head = '9' * 40
                raise aegis.GitHubError('not fast forward', 422)
            self.head = data['sha']
            self.entries = self.new_entries
            return {'object': {'sha': self.head}}
        raise AssertionError((endpoint, method, data))

    def mutations(self):
        return [c for c in self.calls if c[1] != 'GET']


class StateBranchTests(unittest.TestCase):
    def test_new_init_has_state_only_tree_and_no_product_parent(self):
        api = FakeGit(exists=False)
        result = state_branch.initialize('owner/repo', api, aegis.new_state())
        self.assertEqual(result['status'], 'initialized')
        self.assertEqual([e['path'] for e in api.entries], ['aegis-state.json'])
        self.assertEqual(api.new_commit['parents'], [])
        self.assertNotIn('base_tree', next(c[2] for c in api.calls if c[:2] == ('/git/trees', 'POST')))

    def test_existing_init_never_writes(self):
        api = FakeGit()
        with self.assertRaisesRegex(ValueError, 'STATE_EXISTS'):
            state_branch.initialize('owner/repo', api, aegis.new_state())
        self.assertEqual(api.mutations(), [])

    def test_plan_is_read_only_and_identifies_exact_files(self):
        api = FakeGit()
        result = state_branch.isolate('owner/repo', api)
        self.assertEqual(result['remove'], ['.github/workflows/test.yml'])
        self.assertEqual(result['head'], 'a' * 40)
        self.assertEqual(api.mutations(), [])

    def test_migration_preserves_state_product_files_and_parent_history(self):
        api = FakeGit()
        before = copy.deepcopy(api.state)
        result = state_branch.isolate('owner/repo', api, True, 'a' * 40, True)
        self.assertEqual(result['status'], 'isolated')
        self.assertEqual(api.state, before)
        self.assertEqual([e['path'] for e in api.entries], ['aegis-state.json', 'src/app.js'])
        self.assertEqual(api.new_commit['parents'], ['a' * 40])
        patch = [c for c in api.calls if c[1] == 'PATCH']
        self.assertEqual(patch[0][2], {'sha': '4' * 40, 'force': False})

    def test_stale_and_busy_and_unconfirmed_never_mutate(self):
        cases = ['stale', 'lease', 'qa', 'queue', 'confirmation', 'truncated']
        for case in cases:
            with self.subTest(case=case):
                api = FakeGit()
                if case == 'lease': api.state['tasks']['1']['lease'] = {'expires': 0}
                if case == 'qa': api.state['qa'] = {'issue': '1'}
                if case == 'queue': api.state['tasks']['1'].update(state='merge-ready', merge_request={'status': 'sending'})
                if case == 'truncated': api.truncated = True
                with self.assertRaises(ValueError):
                    state_branch.isolate('o/r', api, True,
                                         '0' * 40 if case == 'stale' else 'a' * 40,
                                         case != 'confirmation')
                self.assertEqual(api.mutations(), [])

    def test_concurrent_state_write_is_not_overwritten_or_retried(self):
        api = FakeGit(); api.race = True
        with self.assertRaises(aegis.GitHubError):
            state_branch.isolate('o/r', api, True, 'a' * 40, True)
        self.assertEqual(api.head, '9' * 40)
        self.assertEqual(len([c for c in api.calls if c[1] == 'PATCH']), 1)
        self.assertEqual(len(api.entries), 4)

    def test_unknown_remote_outcome_is_not_retried(self):
        api = FakeGit(); api.timeout = True
        with self.assertRaisesRegex(aegis.WorkflowError, 'REMOTE_UNKNOWN'):
            state_branch.isolate('o/r', api, True, 'a' * 40, True)
        self.assertEqual(len([c for c in api.calls if c[1] == 'PATCH']), 1)

    def test_already_isolated_no_commit(self):
        api = FakeGit()
        api.entries = [e for e in api.entries if not e['path'].startswith('.github/workflows')]
        result = state_branch.isolate('o/r', api, True, 'a' * 40, True)
        self.assertEqual(result['status'], 'already_isolated')
        self.assertEqual(api.mutations(), [])


if __name__ == '__main__':
    unittest.main()
