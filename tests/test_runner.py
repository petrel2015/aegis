"""Deterministic unit tests for the one-shot host runner (transport/host fakes, no network)."""
import json
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/aegis/scripts'))
import run_once as ro


def make_cfg(tmp, argv=None, role='developer'):
    command = Path(tmp) / 'command.json'
    command.write_text(json.dumps(argv or ['fake-agent', '--prompt', '{prompt_file}',
                                           '--workspace', '{workspace}']))
    return ro.load_config(ro.parse_args(['--repo', 'o/r', '--role', role, '--actor', 'dev-1',
        '--workspace', str(tmp), '--command-file', str(command), '--output-dir', str(Path(tmp) / 'out')]))


def scripted_call(responses, log=None):
    """Fake aegis.py transport: mapping subcommand -> result or exception."""
    def call(repo, args, run=None, timeout=120):
        if log is not None:
            log.append(args[0])
        result = responses.get(args[0], responses.get('*', {'status':'ready_to_claim'} if args[0]=='resume' else {'tasks': []}))
        if isinstance(result, Exception):
            raise result
        return result
    return call


class FakeProc:
    def __init__(self, exit_after=None, hang=False, clock=None):
        self.hang, self.exit_after, self.clock, self.killed = hang, exit_after, clock, 0
        self.pid, self.returns = 4242, 0
    def wait(self, timeout=None):
        if self.hang or (self.exit_after is not None and self.returns < self.exit_after):
            self.returns += 1
            if self.clock is not None:
                self.clock[0] += timeout or 0
            raise subprocess.TimeoutExpired('host', timeout)
        return 0
    def poll(self):
        return None if self.hang else 0


def fake_killer(recorder):
    def kill(proc):
        proc.killed = getattr(proc, 'killed', 0) + 1
        recorder.append('killed')
        class Done:
            def wait(self, timeout=None): return 0
        return Done()
    return kill


class RunnerTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
    def tearDown(self):
        self._tmp.cleanup()

    def policy(self, minutes=30):
        return {'policy': {'max_run_minutes': minutes, 'max_issues_per_run': 1},
                'diagnostics': {'ok': True}}

    def task(self, issue=7):
        return {'revision': 1, 'tasks': [{'issue': issue, 'state': 'ready', 'lease': None}],
                'qa_busy': False}  # scan result shape: list of eligible tasks

    def test_empty_scan_never_spawns_host(self):
        log, spawned = [], []
        cfg = make_cfg(self.tmp)
        call = scripted_call({'preflight': self.policy(), 'scan': {'tasks': []}, 'intake': {}}, log)
        def no_spawn(*a, **k):
            spawned.append(a)
            raise AssertionError('host must not be invoked without eligible work')
        with patch.object(ro, 'spawn_host', no_spawn):
            result = ro.run_once(cfg, call=call, spawn=no_spawn, killer=fake_killer([]))
        self.assertEqual(result['status'], 'idle')
        self.assertNotIn('intake', log)  # developer role: no intake call
        self.assertEqual(spawned, [])

    def test_planner_runs_intake_once(self):
        log = []
        cfg = make_cfg(self.tmp, role='planner')
        call = scripted_call({'preflight': self.policy(), 'intake': {}, 'scan': {'tasks': []}}, log)
        result = ro.run_once(cfg, call=call, spawn=lambda *a: (_ for _ in ()).throw(AssertionError('no spawn')),
                             killer=fake_killer([]))
        self.assertEqual(result['status'], 'idle')
        self.assertEqual(log.count('intake'), 1)  # exactly one intake call

    def test_arg_substitution_is_shell_free(self):
        captured = {}
        cfg = make_cfg(self.tmp)
        def spawn(argv, workspace, fh):
            captured['argv'], captured['ws'] = argv, workspace
            class P:
                pid = 99
                def wait(self, timeout=None): return 0
            return P()
        call = scripted_call({'preflight': self.policy(), 'scan': self.task(),
            'claim': {'token': 'tok123', 'task': {'state': 'ready'}},
            'status': {'tasks': {'7': {'state': 'code-review', 'lease': None}}},
            'release': {'ok': True}})
        result = ro.run_once(cfg, call=call, spawn=spawn, killer=fake_killer([]))
        self.assertEqual(result['status'], 'incomplete')
        self.assertFalse(result['released'])
        self.assertEqual(result.get('observed_next_state'), 'code-review')
        self.assertEqual(captured['argv'][0], 'fake-agent')  # argv[0] stays the host command
        self.assertNotIn('{prompt_file}', json.dumps(captured['argv']))
        self.assertNotIn('{workspace}', json.dumps(captured['argv']))
        self.assertIn('prompt.md', ' '.join(captured['argv']))
        prompt = Path(captured['argv'][2]).read_text()
        self.assertIn('tok123', prompt)
        self.assertIn('never run claim again', prompt)

    def test_timeout_kills_tree_and_does_not_claim_completion(self):
        cfg = make_cfg(self.tmp)
        kills = []
        clock = [1000.0]
        proc = FakeProc(hang=True, clock=clock)
        def spawn(argv, workspace, fh):
            return proc
        call = scripted_call({'preflight': self.policy(minutes=1), 'scan': self.task(),
                              'claim': {'token': 't0', 'task': {'state': 'ready'}}})
        result = ro.run_once(cfg, call=call, spawn=spawn, killer=fake_killer(kills), clock=lambda: clock[0])
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(result['killed'])
        self.assertEqual(kills, ['killed'])
        self.assertIsNone(result['worker_exit'])
        self.assertIn('timeout', result['detail'])

    def test_coordination_failure_is_structured_resumable_blocker(self):
        cfg = make_cfg(self.tmp)
        boom = ro.RemoteUnknown('COORD_FAILED preflight: HTTP 502', attempt={'operation': 'op1'})
        result = ro.run_once(cfg, call=scripted_call({'preflight': boom}), killer=fake_killer([]))
        self.assertEqual(result['status'], 'blocked')
        self.assertTrue(result['remote_unknown'])
        self.assertEqual(result['attempt']['operation'], 'op1')
        self.assertEqual(result['attempt']['operation'], 'op1')

    def test_no_release_or_finish_without_owned_lease(self):
        # Host fails (exit 1); task meanwhile advanced by someone else, no lease: never release, never finish.
        cfg = make_cfg(self.tmp)
        released = []
        call = scripted_call({'preflight': self.policy(), 'scan': self.task(),
            'claim': {'token': 'tk', 'task': {'state': 'ready'}},
            'status': {'tasks': {'7': {'state': 'testing', 'lease': None}}},
            'release': {'ok': True}})
        def spawn(argv, workspace, fh):
            class P:
                pid = 5
                def wait(self, timeout=None): return 1
            return P()
        result = ro.run_once(cfg, call=call, spawn=spawn, killer=fake_killer([]))
        self.assertEqual(result['status'], 'incomplete')
        self.assertFalse(result['released'])
        self.assertIn('testing', json.dumps(result['observed_next_state']))

    def test_local_lock_blocks_concurrent_same_scope(self):
        cfg = make_cfg(self.tmp)
        lock_path = Path(cfg.workspace) / '.aegis-local' / 'locks' / (cfg.role + '-' + cfg.actor + '.lock')
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        holder = open(lock_path, 'a+')
        import fcntl
        fcntl.flock(holder.fileno(), fcntl.LOCK_EX)
        result = ro.run_once(cfg, call=scripted_call({}), killer=fake_killer([]))
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('LOCK_BUSY', result['detail'])
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()

    def test_invalid_command_file_and_policy(self):
        with self.assertRaises(Exception):
            make_cfg(self.tmp, argv='not-a-list')
        bad = ro.run_once(make_cfg(self.tmp), call=scripted_call(
            {'preflight': {'policy': {'max_run_minutes': -5, 'max_issues_per_run': 4}}}), killer=fake_killer([]))
        self.assertEqual(bad['status'], 'blocked')
        self.assertIn('max_run_minutes', bad['detail'])
        capped = ro.run_once(make_cfg(self.tmp), call=scripted_call(
            {'preflight': {'policy': {'max_run_minutes': 10, 'max_issues_per_run': 9}},
             'scan': {'tasks': [{'issue': 1}, {'issue': 2}]}
             }), killer=fake_killer([]))
        # two eligible tasks exist, but only one claim attempt for the first item
        self.assertEqual(capped['issue'], 1)


if __name__ == '__main__':
    unittest.main()
