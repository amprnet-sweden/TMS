import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
HOST = "tms.example.test"

spec = importlib.util.spec_from_file_location(
    "lab_tls", Path(__file__).resolve().parents[1] / "scripts/prepare-tls.py"
)
tls = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tls)


class LabTlsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="tms-tls-test-")
        self.directory = Path(self.temporary.name) / "tls"

    def tearDown(self):
        self.temporary.cleanup()

    def fingerprints(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.directory.iterdir()}

    def test_chain_hostname_permissions_and_reuse(self):
        tls.prepare(self.directory, HOST)
        first = self.fingerprints()
        tls.prepare(self.directory, HOST)
        self.assertEqual(first, self.fingerprints())
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        for path in self.directory.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        command = ["openssl", "verify", "-CAfile", str(self.directory / "ca.crt"),
                   "-purpose", "sslserver", "-verify_hostname", HOST,
                   str(self.directory / "server.crt")]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        command[-2] = "wrong.example"
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)

    def test_incomplete_files_are_preserved(self):
        tls.prepare(self.directory, HOST)
        (self.directory / "server.key").unlink()
        before = self.fingerprints()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            tls.prepare(self.directory, HOST)
        self.assertEqual(before, self.fingerprints())

    def test_mismatched_key_is_rejected_without_replacement(self):
        tls.prepare(self.directory, HOST)
        (self.directory / "server.key").write_bytes((self.directory / "ca.key").read_bytes())
        before = self.fingerprints()
        with self.assertRaisesRegex(ValueError, "do not match"):
            tls.prepare(self.directory, HOST)
        self.assertEqual(before, self.fingerprints())


if __name__ == "__main__":
    unittest.main()
