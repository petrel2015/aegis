import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/aegis/scripts'))
import release_pipeline as rp

class ReleasePipelineTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.build=self.root/'build';self.old=self.root/'old';self.build.mkdir();self.old.mkdir();self.sha='a'*40;self.site='https://example.test/app/';self.out=self.root/'run'
  (self.build/'index.html').write_text('new');(self.old/'index.html').write_text('old')
 def prepare(self,**kw):return rp.prepare(self.build,self.old,self.out,self.sha,self.site,**kw)
 def test_preserves_legacy_attribution_domain_and_nojekyll(self):
  for n in ('ATTRIBUTION.md','CNAME','.nojekyll','LICENSE.txt'):(self.old/n).write_text(n)
  m=self.prepare();self.assertEqual(set(m['diff']['retained']),{'ATTRIBUTION.md','CNAME','.nojekyll','LICENSE.txt'})
  for n in m['diff']['retained']:self.assertEqual((self.out/'artifact'/n).read_text(),n)
  self.assertEqual(json.loads((self.out/'artifact/build.json').read_text())['sourceCommit'],self.sha)
 def test_protected_changes_and_unreviewed_deletion_rejected_before_output(self):
  (self.old/'CNAME').write_text('original');(self.build/'CNAME').write_text('different')
  with self.assertRaisesRegex(ValueError,'PROTECTED_CHANGED'):self.prepare()
  self.assertFalse(self.out.exists());(self.build/'CNAME').unlink();(self.old/'readme.html').write_text('public guide')
  with self.assertRaisesRegex(ValueError,'REMOVAL_REVIEW'):self.prepare()
  m=self.prepare(allow_remove=['readme.html']);self.assertIn('readme.html',m['diff']['removed'])
 def test_replaced_hashed_asset_allowed_but_regular_data_not(self):
  (self.old/'assets').mkdir();(self.old/'assets/index-1234abcd.js').write_text('old')
  with self.assertRaisesRegex(ValueError,'REMOVAL_REVIEW'):self.prepare()
  self.prepare(allow_remove=['assets/index-1234abcd.js'])
 def test_rejects_symlinks_private_files_overlap_and_stale_metadata(self):
  for name in ('.env.production','.github/workflows/a.yml','node_modules/a.js'):
   p=self.build/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('secret')
   with self.assertRaisesRegex(ValueError,'ARTIFACT_PRIVATE'):self.prepare()
   p.unlink()
  (self.build/'link').symlink_to(self.old/'index.html')
  with self.assertRaisesRegex(ValueError,'ARTIFACT_SYMLINK'):self.prepare()
  (self.build/'link').unlink();(self.build/'build.json').write_text(json.dumps({'sourceCommit':'b'*40}))
  with self.assertRaisesRegex(ValueError,'BUILD_VERSION'):self.prepare()
 def test_local_tampering_refuses_public_verification(self):
  self.prepare();(self.out/'artifact/index.html').write_text('tampered')
  with self.assertRaisesRegex(ValueError,'ARTIFACT_CHANGED'):rp.verify(self.out,self.root/'verify',lambda url:b'')
 def test_public_files_verified_against_archive(self):
  self.prepare();m,files=rp.load_artifact(self.out)
  from urllib.parse import unquote,urlsplit
  def fetch(url):return files[unquote(urlsplit(url).path.removeprefix('/app/'))]
  r=rp.verify(self.out,self.root/'verify',fetch);self.assertEqual(r['status'],'files_verified');self.assertEqual(r['observed_artifact_digest'],m['artifact_digest']);self.assertEqual(r['exclusions'],[])
 def test_public_mismatch_and_network_error_preserve_unknown(self):
  self.prepare()
  with self.assertRaisesRegex(ValueError,'PUBLIC_FILE_MISMATCH'):rp.verify(self.out,self.root/'fail',lambda url:b'old')
  r=json.loads((self.root/'fail/verification.json').read_text());self.assertEqual(r['status'],'remote_unknown');self.assertNotIn('observed_artifact_digest',r)
  with self.assertRaisesRegex(ValueError,'RUN_EXISTS'):rp.verify(self.out,self.root/'fail',lambda url:b'')
 def test_smoke_runs_actual_command_and_retains_failure(self):
  r=rp.smoke([sys.executable,'-c','print("evidence");raise SystemExit(3)'],self.root/'smoke',self.site)
  self.assertEqual(r['status'],'fail');self.assertEqual(r['exit_code'],3);self.assertIn('evidence',(self.root/'smoke/stdout.log').read_text())
 def test_destination_and_dirty_checkout_block_before_mutation(self):
  self.prepare()
  with patch.object(rp,'command',return_value='dirty'):
   with self.assertRaisesRegex(ValueError,'CHECKOUT_DIRTY'):rp.publish(self.out,self.old,'owner/repo','b'*40,'user authorized')
  with patch.object(rp,'command',side_effect=['','https://github.com/other/repo.git']):
   with self.assertRaisesRegex(ValueError,'DESTINATION_MISMATCH'):rp.publish(self.out,self.old,'owner/repo','b'*40,'user authorized')
 def test_remote_base_change_blocks_publish(self):
  self.prepare()
  with patch.object(rp,'command',side_effect=['','https://github.com/owner/repo.git','main','b'*40,json.dumps({'object':{'sha':'c'*40}})]):
   with self.assertRaisesRegex(ValueError,'REMOTE_BASE_CHANGED'):rp.publish(self.out,self.old,'owner/repo','b'*40,'authorized')
  self.assertEqual((self.old/'index.html').read_text(),'old')

 def test_actual_checkout_extra_file_refuses_unreviewed_removal(self):
  self.prepare();(self.old/'guide.txt').write_text('must preserve')
  with patch.object(rp,'command',side_effect=['','https://github.com/owner/repo.git','main','b'*40,json.dumps({'object':{'sha':'b'*40}})]):
   with self.assertRaisesRegex(ValueError,'PREVIOUS_ARTIFACT_CHANGED'):rp.publish(self.out,self.old,'owner/repo','b'*40,'authorized')
  self.assertTrue((self.old/'guide.txt').exists())
 def test_replay_refused_before_any_git_command(self):
  self.prepare();(self.out/'publish.json').write_text('{}')
  with patch.object(rp,'command') as command:
   with self.assertRaisesRegex(ValueError,'PUBLISH_EXISTS'):rp.publish(self.out,self.old,'owner/repo','b'*40,'authorized')
   command.assert_not_called()
 def test_verification_output_cannot_pollute_retained_artifact(self):
  self.prepare()
  with self.assertRaisesRegex(ValueError,'OUTPUT_OVERLAP'):rp.verify(self.out,self.out/'artifact/check',lambda url:b'')
  rp.load_artifact(self.out)

 def test_dated_public_report_is_not_automatically_deleted(self):
  (self.old/'assets').mkdir();(self.old/'assets/report-20231001.pdf').write_text('report')
  with self.assertRaisesRegex(ValueError,'REMOVAL_REVIEW'):self.prepare()

class ActualGitPublicationTests(unittest.TestCase):
 """Real Git checks/commits; GitHub and push transport never leave the host."""
 def setUp(self):
  import shutil
  if not shutil.which('git'):self.skipTest('git unavailable')
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.checkout=self.root/'checkout';self.checkout.mkdir()
  self.git('init','-b','main');self.git('config','user.email','review@example.invalid');self.git('config','user.name','Offline Review')
  self.git('remote','add','origin','https://github.com/owner/repo.git')
  for name,value in {'index.html':'old','CNAME':'example.test','ATTRIBUTION.md':'credit','.nojekyll':''}.items():(self.checkout/name).write_text(value)
  self.git('add','.');self.git('commit','-m','original artifact');self.base=self.git('rev-parse','HEAD');self.remote=self.base
  self.original_command=rp.command;self.pushes=[]
 def git(self,*args):
  import subprocess
  return subprocess.check_output(['git',*args],cwd=self.checkout,text=True,stderr=subprocess.DEVNULL).strip()
 def prepare(self,tag):
  build=self.root/('build-'+tag);build.mkdir();(build/'index.html').write_text(tag)
  run=self.root/('run-'+tag);rp.prepare(build,self.checkout,run,('a' if tag=='A' else 'b')*40,'https://example.test/')
  return run
 def transport(self,argv,cwd=None,timeout=60):
  if argv[0]=='gh':return json.dumps({'object':{'sha':self.remote}})
  if argv[:2]==['git','push']:
   self.pushes.append(argv);self.remote=argv[3].split(':')[0];return ''
  return self.original_command(argv,cwd,timeout)
 def test_success_retains_files_receipt_and_clean_checkout(self):
  run=self.prepare('A')
  with patch.object(rp,'command',side_effect=self.transport):result=rp.publish(run,self.checkout,'owner/repo',self.base,'user authorized exact destination')
  self.assertEqual(result['status'],'pending');self.assertEqual(len(self.pushes),1)
  self.assertEqual(json.loads((run/'publish.json').read_text())['artifact_commit'],self.git('rev-parse','HEAD'))
  self.assertEqual(json.loads((run/'publish.json').read_text())['status'],'pending')
  _,files=rp.load_artifact(run)
  self.assertTrue(all((self.checkout/name).read_bytes()==data for name,data in files.items()))
  self.assertEqual(self.git('status','--porcelain'),'');self.assertFalse((self.checkout/'.git/aegis-release.lock').exists())
 def test_delayed_concurrent_publisher_cannot_reuse_stale_preflight(self):
  import threading
  first=self.prepare('A');second=self.prepare('B');paused=threading.Event();resume=threading.Event();outcomes=[]
  def transport(argv,cwd=None,timeout=60):
   if argv[:4]==['git','rev-parse','--git-path','aegis-release.lock'] and threading.current_thread().name=='delayed-publisher':
    paused.set()
    if not resume.wait(10):raise RuntimeError('test coordination timeout')
   return self.transport(argv,cwd,timeout)
  def delayed():
   try:outcomes.append(rp.publish(second,self.checkout,'owner/repo',self.base,'authorized'))
   except Exception as error:outcomes.append(error)
  with patch.object(rp,'command',side_effect=transport):
   thread=threading.Thread(target=delayed,name='delayed-publisher');thread.start()
   try:
    self.assertTrue(paused.wait(10));first_result=rp.publish(first,self.checkout,'owner/repo',self.base,'authorized')
   finally:resume.set();thread.join(10)
  self.assertFalse(thread.is_alive());self.assertEqual(first_result['status'],'pending')
  self.assertEqual(len(outcomes),1);self.assertIsInstance(outcomes[0],ValueError);self.assertIn('LOCAL_BASE_CHANGED',str(outcomes[0]))
  self.assertEqual((self.checkout/'index.html').read_text(),'A');self.assertEqual(len(self.pushes),1)
  self.assertFalse((second/'publish.json').exists());self.assertFalse((self.checkout/'.git/aegis-release.lock').exists())
