import base64
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/aegis/scripts'))
import aegis
import bootstrap

HEAD = 'a' * 40
BASE = 'b' * 40
EVIDENCE = {'summary': 'Observed result', 'url': 'https://github.com/org/project/issues/1#issuecomment-1',
            'pr': 2, 'head': HEAD, 'base': BASE, 'tested_commit': 'c' * 40, 'result': 'pass'}

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.s = aegis.mutate(aegis.new_state(), 'register', 1, 'p', now=10, op='register')
    def apply(self, cmd, actor='p', **kwargs):
        self.s = aegis.mutate(self.s, cmd, 1, actor, now=20, **kwargs)
    def stage(self, state):
        self.s['tasks']['1']['state'] = state
    def claim(self, role='planner', actor='p', token='t'):
        self.apply('claim', actor, role=role, token=token)
    def finish(self, target, actor='p', token='t', evidence=None):
        self.apply('finish', actor, token=token, target=target, evidence=evidence or EVIDENCE)
    def test_full_lifecycle(self):
        for current, role, actor, target in [('new','planner','p','design-review'),
          ('design-review','reviewer','r','ready'), ('ready','developer','d','code-review'),
          ('code-review','reviewer','r','testing'), ('testing','qa','q','merge-ready'),
          ('merge-ready','qa','q','done')]:
            self.assertEqual(self.s['tasks']['1']['state'], current)
            self.claim(role, actor)
            self.finish(target, actor)
        self.assertIsNone(self.s['qa'])
        self.assertEqual(len(self.s['tasks']['1']['history']), 6)
    def test_only_one_claim(self):
        self.claim()
        with self.assertRaises(aegis.WorkflowError): self.claim(actor='other')
    def test_immutable_input_on_failure(self):
        original = copy.deepcopy(self.s)
        with self.assertRaises(aegis.WorkflowError): self.claim('qa')
        self.assertEqual(self.s, original)
    def test_no_expired_takeover(self):
        self.claim()
        with self.assertRaises(aegis.WorkflowError):
            aegis.mutate(self.s, 'claim', 1, 'other', role='planner', token='x', now=9999)
        with self.assertRaises(aegis.WorkflowError):
            aegis.mutate(self.s, 'heartbeat', 1, 'p', token='t', now=9999)
    def test_wrong_token_cannot_release(self):
        self.claim()
        with self.assertRaises(aegis.WorkflowError): self.apply('release', token='wrong')
    def test_heartbeat_extends_owned_lease(self):
        self.claim()
        s = aegis.mutate(self.s, 'heartbeat', 1, 'p', token='t', now=100, ttl=200)
        self.assertEqual(s['tasks']['1']['lease']['expires'], 300)
    def test_independent_design_review(self):
        self.claim(); self.finish('design-review')
        with self.assertRaises(aegis.WorkflowError): self.claim('reviewer')
    def test_all_prior_code_authors_excluded(self):
        self.stage('ready'); self.claim('developer', 'd1'); self.finish('code-review', 'd1')
        self.claim('reviewer','r'); self.finish('ready','r')
        self.claim('developer','d2'); self.finish('code-review','d2')
        with self.assertRaises(aegis.WorkflowError): self.claim('reviewer','d1')
    def test_qa_global_slot(self):
        self.stage('testing'); self.claim('qa','q')
        s = aegis.mutate(self.s, 'register', 2, 'p')
        s['tasks']['2']['state'] = 'testing'
        with self.assertRaises(aegis.WorkflowError):
            aegis.mutate(s, 'claim', 2, 'q2', role='qa', token='other')
        self.apply('release','q',token='t')
        self.assertIsNone(self.s['qa'])
    def test_no_skip_review(self):
        self.claim()
        with self.assertRaises(aegis.WorkflowError): self.finish('done')
    def test_qa_requires_exact_integration(self):
        self.stage('testing'); self.claim('qa','q')
        bad = dict(EVIDENCE); bad.pop('tested_commit')
        with self.assertRaises(aegis.WorkflowError): self.finish('merge-ready','q',evidence=bad)
    def test_pre_pr_block(self):
        self.stage('ready'); self.claim('developer','d')
        self.finish('blocked','d',evidence={'summary':'Missing environment','url':'https://example.com/evidence'})
    def test_remote_head_and_base(self):
        self.stage('testing')
        self.s['tasks']['1']['history'] = [{'evidence': EVIDENCE}]
        pr = {'head':{'sha':HEAD},'base':{'sha':BASE,'repo':{'full_name':'o/r'}},'state':'open','draft':False}
        with patch.object(aegis,'gh_api',return_value=pr):
            aegis.validate_remote('o/r',self.s,1,'merge-ready',EVIDENCE)
            with self.assertRaises(aegis.WorkflowError):
                aegis.validate_remote('o/r',self.s,1,'merge-ready',dict(EVIDENCE,head='d'*40))
            with self.assertRaises(aegis.WorkflowError):
                aegis.validate_remote('o/r',self.s,1,'merge-ready',dict(EVIDENCE,base='d'*40))
    def test_review_candidate_mismatch(self):
        self.stage('code-review')
        self.s['tasks']['1']['history'] = [{'evidence':dict(EVIDENCE,head='e'*40)}]
        pr = {'head':{'sha':HEAD},'base':{'repo':{'full_name':'o/r'}},'state':'open','draft':False}
        with patch.object(aegis,'gh_api',return_value=pr):
            with self.assertRaises(aegis.WorkflowError):
                aegis.validate_remote('o/r',self.s,1,'testing',EVIDENCE)
    def test_queue_admission_not_done(self):
        self.stage('merge-ready')
        pr = {'head':{'sha':HEAD},'base':{'repo':{'full_name':'o/r'}},'merged':False}
        with patch.object(aegis,'gh_api',return_value=pr):
            with self.assertRaises(aegis.WorkflowError):
                aegis.validate_remote('o/r',self.s,1,'done',EVIDENCE)
    def test_contents_payload_uses_cas(self):
        with patch.object(aegis,'gh_api') as api:
            aegis.Store('o/r').write(self.s,'previous-sha','operation')
            data=api.call_args.args[3]
            self.assertEqual(data['sha'],'previous-sha')
            self.assertEqual(data['branch'],'aegis-state')
            self.assertEqual(json.loads(base64.b64decode(data['content'])),self.s)
    def test_cas_simulation_two_contenders(self):
        # Simulate server SHA conflict, not a live GitHub concurrency proof.
        remote = {'sha':'s0','state':self.s}
        def api(repo, endpoint, method='GET', data=None):
            if method == 'GET':
                return {'sha':remote['sha'],'content':base64.b64encode(json.dumps(remote['state']).encode()).decode()}
            if data['sha'] != remote['sha']: raise aegis.WorkflowError('conflict')
            remote.update(sha='s1',state=json.loads(base64.b64decode(data['content'])))
        with patch.object(aegis,'gh_api',side_effect=api):
            store=aegis.Store('o/r'); a,sa=store.read(); b,sb=store.read()
            store.write(aegis.mutate(a,'claim',1,'a',role='planner',token='a'),'s0','a')
            with self.assertRaises(aegis.WorkflowError):
                store.write(aegis.mutate(b,'claim',1,'b',role='planner',token='b'),sb,'b')
            self.assertEqual(store.read()[0]['tasks']['1']['lease']['actor'],'a')
    def test_bootstrap_preserves_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            first=bootstrap.bootstrap(tmp)
            config=Path(tmp)/'.github/aegis.json'
            config.write_text('custom policy')
            second=bootstrap.bootstrap(tmp)
            self.assertEqual(config.read_text(),'custom policy')
            self.assertTrue(first['created']); self.assertFalse(second['created'])
    def test_bootstrap_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            (Path(tmp)/'.github').symlink_to(other)
            with self.assertRaises(ValueError): bootstrap.bootstrap(tmp)
    def test_released_author_cannot_review(self):
        self.stage('ready'); self.claim('developer','d1')
        self.apply('release','d1',token='t')
        self.claim('developer','d2'); self.finish('code-review','d2')
        with self.assertRaises(aegis.WorkflowError): self.claim('reviewer','d1')
    def test_recovery_fences_old_token_and_preserves_history(self):
        self.stage('testing'); self.claim('qa','q')
        restored=aegis.recover(self.s,1,'maintainer','Process stopped','testing',now=9999,op='fix')
        self.assertIsNone(restored['qa'])
        self.assertEqual(restored['tasks']['1']['recovery'][0]['prior_lease']['token'],'t')
        with self.assertRaises(aegis.WorkflowError):
            aegis.mutate(restored,'heartbeat',1,'q',token='t',now=10000)
    def test_closed_issue_can_finalize_and_release(self):
        self.stage('merge-ready')
        self.s['tasks']['1']['history']=[{'evidence':EVIDENCE}]
        with tempfile.TemporaryDirectory() as tmp:
            evidence=Path(tmp)/'evidence.json'; evidence.write_text(json.dumps(EVIDENCE))
            self.claim('qa','q')
            pr={'head':{'sha':HEAD},'base':{'repo':{'full_name':'o/r'}},'merged':True}
            def api(repo,endpoint='',method='GET',data=None):
                return pr if endpoint.startswith('/pulls/') else {'state':'closed'}
            with patch.object(aegis.Store,'read',return_value=(self.s,'sha')), patch.object(aegis.Store,'write'), patch.object(aegis,'gh_api',side_effect=api), patch.object(aegis.time,'time',return_value=21):
                result=aegis.main(['--repo','o/r','finish','--issue','1','--actor','q','--token','t','--to','done','--evidence',str(evidence)])
                self.assertEqual(result['task']['state'],'done')
                result=aegis.main(['--repo','o/r','release','--issue','1','--actor','q','--token','t'])
                self.assertIsNone(result['task']['lease'])
    def test_closed_issue_merge_ready_claim(self):
        self.stage('merge-ready')
        with patch.object(aegis.Store,'read',return_value=(self.s,'sha')), patch.object(aegis.Store,'write'), patch.object(aegis,'gh_api',return_value={'state':'closed'}):
            result=aegis.main(['--repo','o/r','claim','--issue','1','--actor','q','--role','qa'])
            self.assertEqual(result['task']['lease']['role'],'qa')
    def test_recover_closed_issue_expired_qa(self):
        self.stage('merge-ready'); self.claim('qa','q')
        with patch.object(aegis.Store,'read',return_value=(self.s,'sha')), patch.object(aegis.Store,'write'), patch.object(aegis,'gh_api',return_value={'state':'closed'}):
            result=aegis.main(['--repo','o/r','recover','--issue','1','--actor','maintainer',
                '--reason','Confirmed crashed QA process stopped','--to','merge-ready','--confirm-stopped'])
            self.assertIsNone(result['task']['lease'])
            self.assertEqual(result['task']['recovery'][0]['prior_lease']['token'],'t')
    def test_network_timeout_never_retries(self):
        import subprocess
        with patch.object(aegis.subprocess,'run',side_effect=subprocess.TimeoutExpired('gh',60)) as run:
            with self.assertRaisesRegex(aegis.WorkflowError,'REMOTE_UNKNOWN'):
                aegis.gh_api('o/r','/contents/state','PUT',{})
            self.assertEqual(run.call_count,1)
    def test_repo_normalization(self):
        self.assertEqual(aegis.repo_name('https://github.com/o/r.git'),'o/r')
        with self.assertRaises(aegis.WorkflowError): aegis.repo_name('https://evil.example/o/r')

if __name__ == '__main__': unittest.main()
