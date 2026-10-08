import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/aegis/scripts'))
import evidence_store
import evidence_publish as ep
import release_build as rb
import release_finalize as rf
import release_pipeline as rp
import release_workflow as rw
import report_publish as report
from release_support import command, fingerprint, read, write


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'; self.source.mkdir()
        for argv in (['git', 'init', '-q'], ['git', 'config', 'user.name', 'Test'],
                     ['git', 'config', 'user.email', 'test@localhost'], ['git', 'remote', 'add', 'origin', 'https://github.com/o/source.git']):
            command(argv, self.source)
        (self.source / 'input').write_text('tracked')
        command(['git', 'add', '.'], self.source); command(['git', 'commit', '-qm', 'initial'], self.source)
        self.sha = command(['git', 'rev-parse', 'HEAD'], self.source)
        self.build_output = self.root / 'dist'; self.build_run = self.root / 'build-run'
        self.site = 'https://o.github.io/site/'
        self.argv = [sys.executable, '-c', "import os,pathlib; p=pathlib.Path(os.environ['AEGIS_BUILD_OUTPUT']); p.mkdir(); (p/'index.html').write_text('<html>fixture</html>')"]

    def build(self, argv=None):
        return rb.build(self.source, self.build_output, self.build_run, 'o/source', argv or self.argv, 'pages')

    def artifact(self):
        self.build(); self.previous = self.root / 'old'; self.previous.mkdir()
        (self.previous / '.nojekyll').write_text('')
        self.artifact_dir = self.root / 'artifact'
        return rb.prepare(self.build_run / 'operation.json', self.previous, self.artifact_dir, self.site)


class BuildTests(Fixtures):
    def test_actual_clean_source_and_output_bound(self):
        result = self.build()
        self.assertEqual(result['source_sha'], self.sha); self.assertEqual(result['exit_code'], 0)
        self.assertEqual(rb.validate(self.build_run / 'operation.json')['files'], result['files'])

    def test_dirty_source_and_stale_output_refused(self):
        (self.source / 'input').write_text('dirty')
        with self.assertRaisesRegex(ValueError, 'SOURCE_DIRTY'): self.build()
        command(['git', 'checkout', '--', 'input'], self.source)
        self.build_output.mkdir()
        with self.assertRaisesRegex(ValueError, 'BUILD_STALE_OUTPUT'): self.build()

    def test_output_tampering_and_source_drift_refused(self):
        self.build(); (self.build_output / 'index.html').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'BUILD_OUTPUT_CHANGED'): rb.validate(self.build_run / 'operation.json')
        (self.source / 'input').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'SOURCE_DIRTY'): rb.validate(self.build_run / 'operation.json')

    def test_failed_build_retained_and_not_reusable(self):
        with self.assertRaisesRegex(ValueError, 'BUILD_FAILED'):
            self.build([sys.executable, '-c', 'print("failure evidence"); raise SystemExit(7)'])
        record = read(self.build_run / 'operation.json')
        self.assertEqual(record['exit_code'], 7); self.assertEqual(record['status'], 'failed')
        self.assertIn('failure evidence', (self.build_run / 'stdout.log').read_text())
        with self.assertRaises(FileExistsError): self.build()

    def test_post_build_source_mutation_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_DIRTY'):
            self.build([sys.executable, '-c', "from pathlib import Path;Path('input').write_text('bad')"])
        self.assertEqual(read(self.build_run / 'operation.json')['status'], 'failed')

    def test_timeout_retains_logs(self):
        with self.assertRaisesRegex(ValueError, 'BUILD_TIMEOUT'):
            rb.build(self.source, self.build_output, self.build_run, 'o/source', [sys.executable, '-u', '-c', 'import time;print("started");time.sleep(60)'], 'pages', 0.1)
        self.assertIn('started', (self.build_run / 'stdout.log').read_text())

    def test_governed_prepare_binds_record_and_keeps_protected(self):
        manifest = self.artifact()
        self.assertIn('build_binding', manifest); self.assertIn('.nojekyll', manifest['files'])
        self.assertEqual(manifest['source_sha'], self.sha)

    def test_wrong_origin_or_overlapping_record_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SOURCE_REPO_MISMATCH'):
            rb.build(self.source, self.build_output, self.build_run, 'other/repo', self.argv, 'pages')
        with self.assertRaisesRegex(ValueError, 'PATH_OVERLAP'):
            rb.build(self.source, self.build_output, self.source / 'records', 'o/source', self.argv, 'pages')


class FinalizeTests(Fixtures):
    def setUp(self):
        super().setUp(); self.manifest = self.artifact(); self.commit = 'c' * 40
        self.records = self.root / 'records'; self.records.mkdir()
        self.publication = self.records / 'publish.json'; self.verification = self.records / 'verify.json'; self.smoke = self.records / 'smoke.json'
        write(self.publication, dict(status='pending', repo='o/site', source_sha=self.sha, artifact_commit=self.commit, branch='main'))
        write(self.verification, dict(status='files_verified', site_url=self.site, observed_source_sha=self.sha,
              observed_artifact_digest=self.manifest['artifact_digest'], files=self.manifest['files'], exclusions=[]))
        write(self.smoke, dict(schema='aegis-smoke-observations/v1', target=self.site, observed_source_sha=self.sha,
              artifact_digest=self.manifest['artifact_digest'], run_id='smoke-original', runtime='browser-test', provenance='project-runner', recorded_at='2026-10-08T00:00:00Z',
              checks=[dict(id='popup', kind='browser', result='pass', initial_state='panel expanded', action='normal click', expected='close works', actual='closed', evidence_url='https://example.test/evidence', viewport='390x844', browser_version='Chromium fixture')]))
        self.plan = dict(source_repo='o/source', artifact_repo='o/site', source=str(self.source), build_output=str(self.build_output), build_record=str(self.build_run / 'operation.json'),
             artifact=str(self.artifact_dir), publication_record=str(self.publication), verification_record=str(self.verification), smoke_record=str(self.smoke),
             deployment_record=str(self.records / 'deployment.json'), site_url=self.site, authorization_ref='fixture authorization', rollback='previous artifact',
             execution_mode='external', deployment_run_id=11, deployment_id=22, workflow_path='dynamic/pages/pages-build-deployment', deployment_environment='github-pages')
        self.responses = {
            'repos/o/site/actions/runs/11': dict(id=11, repository={'full_name':'o/site'}, head_sha=self.commit, status='completed', conclusion='success', path=self.plan['workflow_path']),
            'repos/o/site/deployments/22': dict(id=22, sha=self.commit, environment='github-pages'),
            'repos/o/site/deployments/22/statuses?per_page=1': [dict(state='success', environment_url=self.site, log_url='https://github.com/o/site/actions/runs/11/job/33')],
            'repos/o/site/git/trees/' + self.commit + '?recursive=1': dict(truncated=False, tree=[]),
            'repos/o/site/git/ref/heads/main': {'object': {'sha': self.commit}}}
        _, files = rp.load_artifact(self.artifact_dir)
        self.responses['repos/o/site/git/trees/' + self.commit + '?recursive=1']['tree'] = [dict(path=n, type='blob', mode='100644', sha=hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest()) for n, b in files.items()]

    def get(self, endpoint): return copy.deepcopy(self.responses[endpoint])
    def finish(self): return rf.finalize(self.plan, self.root / 'final', self.get)

    def test_observation_derived_success(self):
        result = self.finish(); self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['artifact_commit'], self.commit); self.assertIn('smoke_record', result['inputs'])
        self.assertTrue((self.root / 'final/observations.json').exists())

    def test_generic_success_wrong_workflow_rejected(self):
        self.responses['repos/o/site/actions/runs/11']['path'] = '.github/workflows/test.yml'
        with self.assertRaisesRegex(ValueError, 'DEPLOYMENT_WORKFLOW'): self.finish()
        self.assertEqual(read(self.root / 'final/operation.json')['status'], 'failed')

    def test_missing_deployment_cannot_be_success(self):
        del self.responses['repos/o/site/deployments/22']
        with self.assertRaises(KeyError): self.finish()
        self.assertEqual(read(self.root / 'final/operation.json')['status'], 'remote_unknown')

    def test_deployment_binding_failures(self):
        for key, value in [('state','failure'), ('environment_url','https://other.test/'), ('log_url','https://github.com/o/site/actions/runs/99')]:
            with self.subTest(key=key):
                responses=copy.deepcopy(self.responses)
                responses['repos/o/site/deployments/22/statuses?per_page=1'][0][key]=value
                with self.assertRaises(ValueError): rf.deployment(self.plan, self.commit, lambda endpoint: responses[endpoint])
        for key, value in [('sha','d'*40), ('environment','staging')]:
            responses=copy.deepcopy(self.responses); responses['repos/o/site/deployments/22'][key]=value
            with self.assertRaises(ValueError): rf.deployment(self.plan, self.commit, lambda endpoint: responses[endpoint])

    def test_zero_exit_only_not_browser_observation(self):
        write(self.smoke, dict(status='pass', exit_code=0, target=self.site))
        with self.assertRaisesRegex(ValueError, 'SMOKE_OBSERVATIONS_REQUIRED'): self.finish()

    def test_smoke_wrong_candidate_or_workaround_missing_steps(self):
        smoke = read(self.smoke); smoke['observed_source_sha'] = 'e'*40; write(self.smoke, smoke)
        with self.assertRaisesRegex(ValueError, 'SMOKE_BINDING'): self.finish()

    def test_partial_file_verification_refused(self):
        record = read(self.verification); record['files'].pop('index.html'); write(self.verification, record)
        with self.assertRaisesRegex(ValueError, 'PUBLIC_FILES_BINDING'): self.finish()

    def test_actual_commit_tree_must_match_artifact(self):
        self.responses['repos/o/site/git/trees/' + self.commit + '?recursive=1']['tree'][0]['sha'] = 'f'*40
        with self.assertRaisesRegex(ValueError, 'ARTIFACT_COMMIT_CONTENT'): self.finish()

    def test_legacy_prepare_cannot_claim_governed_build(self):
        record=read(self.artifact_dir / 'artifact.json'); record.pop('build_binding'); write(self.artifact_dir / 'artifact.json', record)
        with self.assertRaisesRegex(ValueError, 'BUILD_BINDING'): self.finish()

    def test_aegis_requires_real_done_qa_merge_integration(self):
        self.plan.update(execution_mode='aegis', issue=3, source_pr=4)
        qa=dict(result='pass',pr=4,head='a'*40,base='b'*40,tested_commit='d'*40,requirements_digest='req',requirements_version=1)
        task=dict(state='done',requirements={'digest':'req','version':1},history=[dict(**{'from':'testing','to':'merge-ready'},evidence=qa),dict(to='done',evidence={'pr':4,'head':'a'*40})])
        state=dict(revision=9,tasks={'3':task})
        self.responses['repos/o/source/contents/aegis-state.json?ref=aegis-state']=dict(encoding='base64',content=base64.b64encode(json.dumps(state).encode()).decode(),sha='stateblob')
        self.responses['repos/o/source/pulls/4']=dict(merged=True,merge_commit_sha=self.sha,head={'sha':'a'*40},base={'repo':{'full_name':'o/source'}})
        self.responses['repos/o/source/git/commits/'+'d'*40]=dict(parents=[{'sha':'b'*40},{'sha':'a'*40}],tree={'sha':'f'*40})
        self.responses['repos/o/source/git/commits/'+self.sha]=dict(tree={'sha':'f'*40})
        self.assertEqual(self.finish()['status'], 'verified')
        self.responses['repos/o/source/pulls/4']['merge_commit_sha']='e'*40
        with self.assertRaisesRegex(ValueError,'WORKFLOW_MERGE_BINDING'): rf.workflow(self.plan,self.sha,self.get)

    def test_resume_does_not_rewrite_or_repush_unknown_publication(self):
        rw.start(self.plan,self.root / 'plan'); manifest=self.root / 'plan/operation.json'
        before=self.publication.read_bytes()
        self.assertEqual(rw.resume(manifest,self.get)['next_action'],'observe_original_deployment')
        self.responses['repos/o/site/git/ref/heads/main']['object']['sha']='e'*40
        self.assertEqual(rw.resume(manifest,self.get)['status'],'remote_unknown')
        self.assertEqual(self.publication.read_bytes(),before)

    def test_failed_deployment_observation_is_retained_and_not_overwritten(self):
        rw.start(self.plan,self.root/'plan'); manifest=self.root/'plan/operation.json'
        with patch.object(rf,'deployment',side_effect=ValueError('DEPLOYMENT_STATUS')):
            with self.assertRaisesRegex(ValueError,'DEPLOYMENT_STATUS'): rw.observe(manifest,11,22)
        record=read(self.plan['deployment_record'])
        self.assertEqual(record['status'],'remote_unknown'); self.assertEqual(record['deployment_run_id'],11)
        with patch.object(rf,'deployment') as observer:
            with self.assertRaises(FileExistsError): rw.observe(manifest,11,22)
            observer.assert_not_called()

    def test_browser_environment_and_step_observations_required(self):
        smoke=read(self.smoke); smoke['checks'][0].pop('initial_state'); write(self.smoke,smoke)
        with self.assertRaisesRegex(ValueError,'SMOKE_CHECK'): self.finish()

    def test_reconciled_unknown_publication_can_finalize_without_rewriting_original(self):
        publication=read(self.publication); publication['status']='remote_unknown'; write(self.publication,publication)
        original=self.publication.read_bytes()
        rw.start(self.plan,self.root/'plan'); manifest=self.root/'plan/operation.json'
        write(self.plan['deployment_record'],dict(status='observed',manifest_digest=fingerprint(manifest),deployment_run_id=11,deployment_id=22))
        self.assertEqual(rw.resume(manifest,self.get)['next_action'],'finalize_new_attempt')
        result=rf.finalize(rw.observed_plan(manifest),self.root/'final',self.get)
        self.assertEqual(result['status'],'verified')
        self.assertEqual(self.publication.read_bytes(),original)
        observations=read(self.root/'final/observations.json')
        self.assertEqual(observations['publication_reconciliation']['artifact_commit'],self.commit)

    def test_unknown_publication_absent_or_moved_ref_cannot_finalize(self):
        publication=read(self.publication); publication['status']='remote_unknown'; write(self.publication,publication)
        original=self.publication.read_bytes()
        self.responses['repos/o/site/git/ref/heads/main']['object']['sha']='e'*40
        with self.assertRaisesRegex(ValueError,'PUBLICATION_REF_UNKNOWN_OR_MOVED'): self.finish()
        self.assertEqual(self.publication.read_bytes(),original)

    def test_finalize_overlapping_directories_and_aliases_leave_inputs_unchanged(self):
        def snapshot(): return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        alias=self.root/'artifact-alias'; alias.symlink_to(self.artifact_dir,target_is_directory=True)
        before=snapshot()
        destinations=[self.artifact_dir/'artifact/corrupt-final',self.source/'record',self.build_output/'record',
                      self.records/'record',self.build_run/'record',alias/'artifact/corrupt-final']
        for output in destinations:
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError,'PATH_OVERLAP'): rf.finalize(self.plan,output,self.get)
                self.assertEqual(snapshot(),before)
                rp.load_artifact(self.artifact_dir)

    def test_start_and_observe_do_not_write_into_artifact_or_source(self):
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'PATH_OVERLAP'): rw.start(self.plan,self.artifact_dir/'artifact/bad-plan')
        self.assertEqual({str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()},before)
        bad_plan=dict(self.plan,deployment_record=str(self.source/'bad-observation.json'))
        # A malformed/externally supplied manifest is read-only input, not authority to overwrite source.
        manifest=self.root/'bad-manifest.json';write(manifest,dict(schema='aegis-release-plan/v1',plan=bad_plan))
        with patch.object(rf,'deployment') as observer:
            with self.assertRaisesRegex(ValueError,'PATH_OVERLAP'): rw.observe(manifest,11,22)
            observer.assert_not_called()
        self.assertFalse((self.source/'bad-observation.json').exists())

    def test_build_bound_prepare_cannot_dirty_source(self):
        with self.assertRaisesRegex(ValueError,'PATH_OVERLAP'):
            rb.prepare(self.build_run/'operation.json',self.previous,self.source/'bad-artifact',self.site)
        self.assertEqual(command(['git','status','--porcelain'],self.source),'')


class EvidencePublicationTests(Fixtures):
    def sealed(self):
        run=evidence_store.new_run(self.root/'runs','o/source',3,'developer')
        directory=Path(run['directory']); (directory/'test.log').write_text('actual fixture output')
        evidence_store.seal(directory,dict(candidate_sha=self.sha,environment=dict(runtime='python',build_mode='test',target='local fixture')))
        self.remote=self.root/'remote.git'; command(['git','init','--bare','-q',str(self.remote)])
        return directory

    def test_real_bare_remote_orphan_only_evidence_and_readonly_resume(self):
        directory=self.sealed(); output=self.root/'upload'
        result=ep.publish(directory,output,'o/source','authorized fixture',str(self.remote))
        self.assertEqual(result['status'],'published')
        self.assertEqual(command(['git','rev-list','--parents','-n','1',result['commit']],self.remote),result['commit'])
        names=command(['git','ls-tree','-r','--name-only',result['commit']],self.remote).splitlines()
        self.assertEqual(set(names),{'run.json','manifest.json','test.log'})
        original=(output/'operation.json').read_bytes(); self.assertEqual(ep.resume(output)['status'],'published')
        self.assertEqual((output/'operation.json').read_bytes(),original)
        with self.assertRaises(FileExistsError): ep.publish(directory,output,'o/source','authorized fixture',str(self.remote))

    def test_workflow_and_tampering_rejected(self):
        directory=self.sealed(); (directory/'test.log').write_text('tampered')
        with self.assertRaisesRegex(ValueError,'EVIDENCE_CHANGED'): ep.publish(directory,self.root/'upload','o/source','fixture',str(self.remote))

    def test_before_and_after_push_interruption_never_retries(self):
        directory=self.sealed(); original=ep.command
        def interrupted(argv,*args,**kwargs):
            if argv[:2]==['git','push']:
                original(argv,*args,**kwargs)
                raise subprocess.TimeoutExpired(argv,60)
            return original(argv,*args,**kwargs)
        output=self.root/'upload'
        with patch.object(ep,'command',side_effect=interrupted):
            with self.assertRaises(subprocess.TimeoutExpired): ep.publish(directory,output,'o/source','fixture',str(self.remote))
        self.assertEqual(read(output/'operation.json')['status'],'remote_unknown')
        self.assertEqual(ep.resume(output)['status'],'published')
        ref=read(output/'operation.json')['ref']; command(['git','update-ref','-d',ref],self.remote)
        with patch.object(ep,'command',wraps=original) as observed:
            self.assertEqual(ep.resume(output)['status'],'remote_unknown')
            self.assertFalse(any(call.args[0][:2]==['git','push'] for call in observed.call_args_list))

    def test_workflow_tree_and_destination_rejected(self):
        directory=self.sealed()
        with self.assertRaisesRegex(ValueError,'EVIDENCE_DESTINATION'): ep.publish(directory,self.root/'wrong','other/repo','fixture',str(self.remote))
        # Build another valid sealed run containing a workflow, then refuse publication.
        run=evidence_store.new_run(self.root/'runs','o/source',3,'developer'); other=Path(run['directory'])
        (other/'.github/workflows').mkdir(parents=True); (other/'.github/workflows/test.yml').write_text('name: should not publish')
        evidence_store.seal(other,dict(candidate_sha=self.sha,environment=dict(runtime='python',build_mode='test',target='local fixture')))
        with self.assertRaisesRegex(ValueError,'EVIDENCE_WORKFLOW'): ep.publish(other,self.root/'workflow','o/source','fixture',str(self.remote))

    def test_push_failure_before_effect_preserves_commit_and_stays_unknown(self):
        directory=self.sealed(); original=ep.command; output=self.root/'upload'
        def interrupted(argv,*args,**kwargs):
            if argv[:2]==['git','push']: raise subprocess.TimeoutExpired(argv,60)
            return original(argv,*args,**kwargs)
        with patch.object(ep,'command',side_effect=interrupted):
            with self.assertRaises(subprocess.TimeoutExpired): ep.publish(directory,output,'o/source','fixture',str(self.remote))
        record=read(output/'operation.json'); self.assertEqual(len(record['commit']),40)
        self.assertEqual(ep.resume(output)['status'],'remote_unknown')
        self.assertIsNone(ep.remote_head(str(self.remote),record['ref']))


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup); self.root=Path(self.temp.name)
        self.record_id='b6b9a2dd-78de-400e-bfdd-ae0c320548d0'
    def test_after_effect_timeout_reconciles_original_without_repost(self):
        comments=[]
        def post(endpoint,payload):
            comments.append(dict(id=8,body=payload['body'],html_url='https://github.com/o/r/issues/3#issuecomment-8'))
            raise subprocess.TimeoutExpired('gh',60)
        with patch.object(report,'pages',return_value=comments),patch.object(report,'api',side_effect=post) as effect:
            with self.assertRaises(subprocess.TimeoutExpired): report.publish('report',self.root/'op','o/r',3,self.record_id,'fixture authorized')
            self.assertEqual(effect.call_count,1)
            original=(self.root/'op/operation.json').read_bytes()
            self.assertEqual(report.resume(self.root/'op')['status'],'published'); self.assertEqual(effect.call_count,1)
            self.assertEqual(original,(self.root/'op/operation.json').read_bytes())
    def test_incomplete_pagination_never_posts(self):
        with patch.object(report,'pages',side_effect=ValueError('PAGINATION_INCOMPLETE')),patch.object(report,'api') as effect:
            with self.assertRaisesRegex(ValueError,'PAGINATION_INCOMPLETE'): report.publish('report',self.root/'op','o/r',3,self.record_id,'fixture authorized')
            effect.assert_not_called()
    def test_same_record_with_changed_content_is_not_reused(self):
        comments=[dict(id=8,body='different\n<!-- aegis-report:'+self.record_id+' -->',html_url='https://github.com/o/r/issues/3#issuecomment-8')]
        with patch.object(report,'pages',return_value=comments),patch.object(report,'api') as effect:
            with self.assertRaisesRegex(ValueError,'REPORT_CONTENT_MISMATCH'): report.publish('report',self.root/'op','o/r',3,self.record_id,'fixture authorized')
            effect.assert_not_called()
