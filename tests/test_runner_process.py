"""Offline forward tests using actual OS processes, without GitHub access."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/aegis/scripts'
sys.path.insert(0, str(SCRIPTS))
import run_once as runner


def alive(pid):
    # Orphan zombies on Linux are stopped, though kill(pid, 0) still succeeds.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path('/proc') / str(pid) / 'stat'
    try:
        if stat.read_text().rsplit(')', 1)[1].split()[0] == 'Z':
            return False
    except (FileNotFoundError, PermissionError):
        pass
    return True


def wait_until(predicate, seconds=5):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return True
        time.sleep(.02)
    return predicate()


@unittest.skipUnless(os.name == 'posix', 'runner supports Linux/macOS process groups')
class RunnerProcessTests(unittest.TestCase):
    def test_operator_signals_stop_host_and_record_blocker(self):
        source = '''import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, sys.argv[1])
import run_once as r
p = Path(sys.argv[2])
cfg = SimpleNamespace(repo='o/r', actor='a', role='developer', workspace=str(p),
    output_dir=str(p/'out'), command_file=p/'cmd.json', heartbeat_interval=300,
    argv=[sys.executable, '-c', 'import time;time.sleep(60)'])
def call(repo, args, **kwargs):
    return {'preflight': {'policy': {'max_run_minutes': 30, 'max_issues_per_run': 1}},
            'scan': {'tasks': [{'issue': 1}]},
            'claim': {'token': 't', 'task': {'state': 'ready', 'history': []}}}[args[0]]
def spawn(*args):
    proc = r.spawn_host(*args)
    (p/'child.pid').write_text(str(proc.pid))
    return proc
r.run_once(cfg, call=call, spawn=spawn)
'''
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                proc = subprocess.Popen([sys.executable, '-c', source, str(SCRIPTS), temp],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                child = None
                try:
                    self.assertTrue(wait_until(lambda: (root/'child.pid').exists()))
                    child = int((root/'child.pid').read_text())
                    proc.send_signal(sig)
                    stdout, stderr = proc.communicate(timeout=15)
                    self.assertEqual(proc.returncode, 0, stderr)
                    result = json.loads(stdout)
                    self.assertEqual(result['status'], 'blocked')
                    self.assertIn('INTERRUPTED', result['detail'])
                    self.assertTrue(wait_until(lambda: not alive(child)), 'host survived runner signal')
                    self.assertTrue((Path(result['run_dir'])/'result.json').is_file())
                finally:
                    if proc.poll() is None:
                        proc.kill()
                    proc.communicate()
                    if child is not None and alive(child):
                        os.killpg(child, signal.SIGKILL)

    def test_coord_timeout_stops_descendants_and_keeps_attempt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pid_file = root/'child.pid'
            script = root/'fake_aegis.py'
            script.write_text(
                "import subprocess,sys,time,json\nfrom pathlib import Path\n"
                "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
                f"Path({str(pid_file)!r}).write_text(str(p.pid))\n"
                "print(json.dumps({'phase':'attempt','operation':'op-live','token':'claim-live'}),file=sys.stderr,flush=True)\n"
                "time.sleep(60)\n")
            child = None
            try:
                with patch.object(runner, 'AEGIS', script):
                    with self.assertRaises(runner.RemoteUnknown) as caught:
                        runner.call_aegis('o/r', ['claim'], timeout=1)
                child = int(pid_file.read_text())
                self.assertEqual(caught.exception.attempt,
                                 {'phase': 'attempt', 'operation': 'op-live', 'token': 'claim-live'})
                self.assertTrue(wait_until(lambda: not alive(child)), 'coordination child survived timeout')
            finally:
                if child is None and pid_file.exists():
                    child = int(pid_file.read_text())
                if child is not None and alive(child):
                    os.kill(child, signal.SIGKILL)

    def test_old_handoff_and_new_other_claim_never_complete_current_run(self):
        cfg = SimpleNamespace(repo='o/r', actor='a')
        history = [
            {'from': 'ready', 'to': 'code-review', 'actor': 'a', 'claim_token': 'old'},
            {'from': 'code-review', 'to': 'ready', 'actor': 'reviewer'},
            {'from': 'ready', 'to': 'code-review', 'actor': 'other', 'claim_token': 'other-token'}]
        task = {'state': 'code-review', 'lease': None, 'history': history}
        call = lambda *args, **kwargs: {'tasks': {'1': task}}
        def inspect():
            return runner.inspect_after_exit(cfg, 1, 'current', 'ready', 0, call, None, history_start=2)
        self.assertEqual(inspect()['status'], 'incomplete')
        history[-1]['actor'] = 'a'  # same stable actor in a different claim also cannot count
        self.assertEqual(inspect()['status'], 'incomplete')
        history[-1]['claim_token'] = 'current'
        self.assertEqual(inspect()['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
