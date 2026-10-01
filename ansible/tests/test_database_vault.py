"""Exercise real vault encryption and credential preservation with temporary secrets."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class DatabaseVaultTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tms-vault-test-")
        self.root = Path(self.temporary.name)
        (self.root / "venv").symlink_to(Path(sys.executable).parent.parent)
        self.environment = dict(os.environ, TMS_CONTROLLER_DIR=str(self.root))
        self.script = Path(__file__).resolve().parents[1] / "scripts/prepare-database-vault.py"

    def tearDown(self):
        self.temporary.cleanup()

    def run_setup(self):
        return subprocess.run(
            [sys.executable, str(self.script)], env=self.environment,
            capture_output=True, text=True,
        )

    def hashes(self):
        return {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (self.root / "secrets").iterdir()
        }

    def test_creates_encrypted_files_and_reuses_identical_credentials(self):
        first = self.run_setup()
        self.assertEqual(first.returncode, 0, first.stderr)
        private = self.root / "secrets"
        self.assertEqual(private.stat().st_mode & 0o777, 0o700)
        for name in ("vault.key", "vault.yml"):
            self.assertEqual((private / name).stat().st_mode & 0o777, 0o600)
        self.assertTrue((private / "vault.yml").read_bytes().startswith(b"$ANSIBLE_VAULT;"))
        before = self.hashes()
        second = self.run_setup()
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(before, self.hashes())

    def test_missing_vault_does_not_replace_the_key(self):
        self.assertEqual(self.run_setup().returncode, 0)
        (self.root / "secrets/vault.yml").unlink()
        before = self.hashes()
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Incomplete vault/key pair", result.stderr)
        self.assertEqual(before, self.hashes())

    def test_wrong_key_does_not_overwrite_the_vault(self):
        self.assertEqual(self.run_setup().returncode, 0)
        (self.root / "secrets/vault.key").write_text("intentionally-wrong-test-key\n")
        before = self.hashes()
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.hashes())


if __name__ == "__main__":
    unittest.main()
