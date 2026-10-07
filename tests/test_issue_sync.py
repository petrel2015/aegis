"""Fault-injected projection tests; all GitHub traffic is simulated."""
import copy
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/aegis/scripts'))
import aegis

class MemoryStore:
    repo = 'o/r'
    def __init__(self, state):
        self.state = copy.deepcopy(state)
        self.version = 1
    def read(self):
        return copy.deepcopy(self.state), str(self.version)
    def write(self, state, sha, operation):
        if sha != str(self.version):
            raise aegis.WorkflowError('CAS conflict')
        self.state = copy.deepcopy(state)
        self.version += 1

class FakeGitHub:
    def __init__(self):
        self.labels = {'bug', 'aegis:intake', 'aegis:ready', 'custom'}
        self.definitions = set(self.labels)
        self.comments = []
        self.post_attempts = 0
        self.failure = None
        self.after_add = None
    def api(self, repo, endpoint='', method='GET', data=None):
        if endpoint.startswith('/labels/'):
            name = unquote(endpoint.split('/labels/')[1])
            if name not in self.definitions:
                raise aegis.GitHubError('not found', 404)
            return {'name': name}
        if endpoint == '/labels':
            if self.failure == 'label-permission':
                raise aegis.GitHubError('forbidden',403)
            self.definitions.add(data['name'])
            return data
        if '/comments' in endpoint:
            if method == 'GET':
                page = int(endpoint.split('page=')[-1])
                return self.comments[(page-1)*100:page*100]
            self.post_attempts += 1
            if self.failure == 'post-before':
                raise aegis.WorkflowError('REMOTE_UNKNOWN')
            comment = {'body': data['body'], 'html_url': f'https://github.com/o/r/issues/1#issuecomment-{len(self.comments)+1}'}
            self.comments.append(comment)
            if self.failure == 'post-after':
                raise aegis.WorkflowError('REMOTE_UNKNOWN')
            return comment
        if '/labels/' in endpoint and method == 'DELETE':
            self.labels.discard(unquote(endpoint.split('/labels/')[1]))
            return None
        if '/labels' in endpoint:
            if method == 'GET':
                return [{'name': n} for n in self.labels]
            self.labels.update(data['labels'])
            if self.after_add:
                self.after_add()
            return [{'name': n} for n in self.labels]
        raise AssertionError(endpoint)

class IssueSyncTests(TestCase):
    def setUp(self):
        state = aegis.new_state()
        state = aegis.mutate(state,'register',1,'p',now=1,op='register')
        state = aegis.mutate(state,'claim',1,'p',role='planner',token='t',now=2)
        state = aegis.mutate(state,'finish',1,'p',token='t',target='blocked',now=3,
            evidence={'summary':'Missing access; maintainer must grant permission',
                      'url':'https://github.com/o/r/issues/1#issuecomment-3'},op='blocked')
        self.store = MemoryStore(state)
        self.github = FakeGitHub()
    def sync(self):
        with patch.object(aegis,'gh_api',side_effect=self.github.api):
            return aegis.sync_issue(self.store,1)
    def test_blocked_label_comment_and_unrelated_labels(self):
        self.assertEqual(self.sync()['status'],'synced')
        self.assertEqual(self.github.labels,{'bug','custom','aegis:intake','aegis:blocked'})
        self.assertIn('Missing access',self.github.comments[-1]['body'])
        self.assertIn('maintainer',self.github.comments[-1]['body'])
        self.assertEqual(self.store.state['tasks']['1']['state'],'blocked')
        self.assertEqual(self.store.state['last_operation'],'blocked')
    def test_repeated_sync_does_not_repeat_comments(self):
        self.sync(); count=self.github.post_attempts
        self.sync()
        self.assertEqual(count,self.github.post_attempts)
    def test_label_failure_keeps_transition_and_resumes(self):
        self.github.failure='label-permission'
        self.assertEqual(self.sync()['status'],'pending')
        self.assertEqual(self.store.state['tasks']['1']['state'],'blocked')
        self.assertEqual(self.github.post_attempts,0)
        self.github.failure=None
        self.assertEqual(self.sync()['status'],'synced')
    def test_timeout_after_post_reconciles_without_duplicate(self):
        self.github.failure='post-after'
        self.assertEqual(self.sync()['status'],'pending')
        self.assertEqual(self.github.post_attempts,1)
        self.github.failure=None
        self.assertEqual(self.sync()['status'],'synced')
        self.assertEqual(self.github.post_attempts,2) # second distinct event only
        self.assertEqual(len(self.github.comments),2)
    def test_timeout_before_post_never_blindly_reposts(self):
        self.github.failure='post-before'
        self.sync(); self.github.failure=None
        self.assertEqual(self.sync()['status'],'pending')
        self.assertEqual(self.github.post_attempts,1)
    def test_cas_conflict_prevents_comment_post(self):
        with patch.object(self.store,'write',side_effect=aegis.WorkflowError('CAS conflict')):
            self.assertEqual(self.sync()['status'],'pending')
        self.assertEqual(self.github.post_attempts,0)
    def test_paginated_reconciliation(self):
        self.github.comments=[{'body':'unrelated','html_url':'https://example.test'}]*100
        self.github.failure='post-after';self.sync();self.github.failure=None
        self.assertEqual(self.sync()['status'],'synced')
        self.assertEqual(self.github.post_attempts,2)
    def test_legacy_snapshot_includes_blocker(self):
        del self.store.state['tasks']['1']['issue_events']
        self.assertEqual(self.sync()['status'],'synced')
        self.assertEqual(len(self.github.comments),1)
        self.assertIn('Missing access',self.github.comments[0]['body'])
    def test_manual_label_does_not_change_state(self):
        self.github.labels.add('aegis:done')
        self.sync()
        self.assertNotIn('aegis:done',self.github.labels)
        self.assertEqual(self.store.state['tasks']['1']['state'],'blocked')
    def test_recovery_removes_blocked_and_records_reason(self):
        self.sync()
        self.store.state=aegis.recover(self.store.state,1,'m','Access restored, old process stopped','new',now=5,op='recovery')
        self.assertEqual(self.sync()['status'],'synced')
        self.assertIn('aegis:new',self.github.labels)
        self.assertNotIn('aegis:blocked',self.github.labels)
        self.assertIn('Access restored',self.github.comments[-1]['body'])
    def test_state_drift_reports_pending_then_converges(self):
        def drift():
            self.store.state=aegis.recover(self.store.state,1,'m','Resolved','new',now=5,op='recovery')
            self.store.version+=1
            self.github.after_add=None
        self.github.after_add=drift
        self.assertEqual(self.sync()['status'],'pending')
        self.assertEqual(self.sync()['status'],'synced')
        self.assertEqual(self.github.labels & aegis.MANAGED_LABELS,{'aegis:new'})
    def test_heartbeat_does_not_create_events(self):
        s=aegis.mutate(aegis.new_state(),'register',2,'p',now=1)
        s=aegis.mutate(s,'claim',2,'p',role='planner',token='t',now=2)
        s=aegis.mutate(s,'heartbeat',2,'p',token='t',now=3)
        s=aegis.mutate(s,'release',2,'p',token='t',now=4)
        self.assertEqual(len(s['tasks']['2']['issue_events']),1)

    def test_concurrent_sync_cannot_post_reserved_event(self):
        observed=[]
        original=self.github.api
        def concurrent(repo, endpoint='', method='GET', data=None):
            if endpoint.endswith('/comments') and method=='POST':
                # A second worker starts after reservation, before first POST completes.
                with patch.object(aegis,'gh_api',side_effect=original):
                    observed.append(aegis.sync_issue(self.store,1))
            return original(repo,endpoint,method,data)
        with patch.object(aegis,'gh_api',side_effect=concurrent):
            result=aegis.sync_issue(self.store,1)
        self.assertEqual(result['status'],'synced')
        self.assertTrue(all(x['status']=='pending' for x in observed))
        self.assertEqual(self.github.post_attempts,2)
    def test_failed_state_commit_never_projects(self):
        with patch.object(aegis.Store,'read',return_value=(aegis.new_state(),'sha')), \
             patch.object(aegis.Store,'write',side_effect=aegis.WorkflowError('conflict')), \
             patch.object(aegis,'gh_api',return_value={'state':'open'}), \
             patch.object(aegis.policy,'load_policy',return_value={}), \
             patch.object(aegis.policy,'intake_issue',return_value={}), \
             patch.object(aegis,'sync_issue') as project:
            with self.assertRaises(aegis.WorkflowError):
                aegis.main(['--repo','o/r','register','--issue','1','--actor','p'])
            project.assert_not_called()
