import sys,json,subprocess,tempfile,tarfile,io
from pathlib import Path
head='3d236b3cb5efd3fbce9d9bfc4e66a15e8b8e9ba8'
root=Path(tempfile.mkdtemp(prefix='aegis-pr4-repro-'));candidate=root/'candidate';candidate.mkdir()
raw=subprocess.check_output(['git','archive',head],cwd='/private/tmp/aegis-release-b6406b')
with tarfile.open(fileobj=io.BytesIO(raw)) as archive:archive.extractall(candidate,filter='data')
sys.path.insert(0,str(candidate/'skills/aegis/scripts'));sys.path.insert(0,str(candidate/'tests'))
from test_release_reliability import FinalizeTests
import release_workflow as rw,release_finalize as rf,release_pipeline as rp
from release_support import write,read,fingerprint
f=FinalizeTests();f.setUp()
try:
 publication=read(f.publication);publication['status']='remote_unknown';write(f.publication,publication);original=f.publication.read_bytes()
 rw.start(f.plan,f.root/'plan');manifest=f.root/'plan/operation.json'
 write(f.plan['deployment_record'],{'status':'observed','manifest_digest':fingerprint(manifest),'deployment_run_id':11,'deployment_id':22})
 resume=rw.resume(manifest,f.get);print('candidate',head);print('F-2 resume',resume['status'],resume['next_action'])
 assert resume['next_action']=='finalize_new_attempt'
 try:rf.finalize(f.plan,f.root/'final-unknown',f.get)
 except ValueError as e:assert str(e)=='PUBLICATION_BINDING';print('F-2 finalize fails',str(e))
 else:raise AssertionError('F-2 not reproduced')
 assert f.publication.read_bytes()==original
 try:rf.finalize(f.plan,f.artifact_dir/'artifact'/'corrupt-final',f.get)
 except ValueError as e:assert str(e)=='ARTIFACT_CHANGED';print('F-3 nested output fails',str(e))
 try:rp.load_artifact(f.artifact_dir)
 except ValueError as e:assert str(e)=='ARTIFACT_CHANGED';print('F-3 retained artifact corrupted',str(e))
 else:raise AssertionError('F-3 not reproduced')
 print('PASS both findings reproduced on immutable candidate with local/provider fixtures; no live effects')
finally:f.doCleanups()
