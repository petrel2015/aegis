"""Full process boundary test with a local fake GitHub transport; never uses network."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

class CLITests(unittest.TestCase):
    def test_lifecycle_through_fake_gh(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / 'gh'
            shutil.copyfile(root/'tests/fixtures/gh', fake)
            fake.chmod(0o755)
            result = subprocess.run([sys.executable, str(root/'tests/fixtures/lifecycle.py'),
                str(root/'skills/aegis/scripts/aegis.py'), tmp],
                text=True, capture_output=True, timeout=30,
                env=dict(os.environ, PATH=str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH']))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS 21 CLI invocations',result.stdout)
