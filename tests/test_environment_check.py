import errno
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch, MagicMock

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/aegis/scripts/environment_check.py'
SPEC = importlib.util.spec_from_file_location('environment_check', SCRIPT)
environment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(environment)


class EnvironmentCheckTests(unittest.TestCase):
    def test_missing_tool_does_not_execute(self):
        with patch.object(environment.shutil, 'which', return_value=None), patch.object(environment.subprocess, 'run') as run:
            self.assertEqual(environment.check_tool('git', ['git', '--version'])['status'], 'missing')
            run.assert_not_called()

    def test_version_timeout_and_failure_structured(self):
        with patch.object(environment.shutil, 'which', return_value='/bin/tool'):
            with patch.object(environment.subprocess, 'run', side_effect=subprocess.TimeoutExpired('tool', 5)):
                self.assertEqual(environment.check_tool('gh', ['gh', '--version'])['diagnostic'], 'version_timeout')
            with patch.object(environment.subprocess, 'run', return_value=subprocess.CompletedProcess([], 9, '', 'private diagnostic')):
                result = environment.check_tool('gh', ['gh', '--version'])
                self.assertEqual(result['exit_code'], 9)
                self.assertNotIn('private', str(result))

    def test_non_shell_version_and_no_auth_probe(self):
        with patch.object(environment.shutil, 'which', return_value='/bin/gh'), patch.object(environment.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'gh version 1\nextra', '')) as run:
            self.assertEqual(environment.check_tool('gh', ['gh', '--version'])['version'], 'gh version 1')
            self.assertEqual(run.call_args.args[0], ['/bin/gh', '--version'])
            self.assertNotIn('shell', run.call_args.kwargs)

    def test_localhost_error_classifies_only_permission(self):
        for error, expected in [(errno.EPERM, 'environment_restricted'), (errno.EACCES, 'environment_restricted'), (errno.EADDRINUSE, 'probe_failed')]:
            fake = MagicMock()
            fake.__enter__.return_value.bind.side_effect = OSError(error, 'test')
            with patch.object(environment.socket, 'socket', return_value=fake):
                self.assertEqual(environment.check_localhost()['status'], expected)
                fake.__exit__.assert_called_once()

    def test_log_restriction_never_means_tests_pass(self):
        result = environment.classify_log("Error: listen EPERM: operation not permitted 127.0.0.1\nFAIL calculation: expected 2 got 3")
        self.assertEqual(result['category'], 'environment_restricted')
        self.assertEqual(result['test_result'], 'undetermined')
        self.assertIn('every failing test', result['scope'])
        self.assertEqual(environment.classify_log('FAIL expected 2 got 3')['category'], 'unknown_test_failure')
        self.assertEqual(environment.classify_log('read EPERM private file')['category'], 'unknown_test_failure')
        self.assertEqual(environment.classify_log('bind EADDRINUSE')['category'], 'unknown_test_failure')

    def test_node_multiline_and_unrelated_distant_error(self):
        self.assertEqual(environment.classify_log("Error: operation not permitted\n code: 'EPERM',\n syscall: 'listen'")['category'], 'environment_restricted')
        self.assertEqual(environment.classify_log('EPERM\n' + 'unrelated\n' * 10 + 'listen')['category'], 'unknown_test_failure')

    def test_localhost_opt_in_and_dependencies_aggregated(self):
        with patch.object(environment, 'check_tool', return_value={'status': 'available'}), patch.object(environment, 'check_localhost') as listen:
            self.assertEqual(environment.probe()['status'], 'observed')
            listen.assert_not_called()
        with patch.object(environment, 'check_tool', return_value={'status': 'missing'}):
            self.assertEqual(environment.probe()['status'], 'needs_attention')

    def test_isolated_cli_help(self):
        result = subprocess.run(['python3', str(SCRIPT), '--help'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--localhost', result.stdout)


if __name__ == '__main__':
    unittest.main()
