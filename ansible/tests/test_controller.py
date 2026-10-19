"""Exercise shared storage guards and error handling without real deployment secrets."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from controller import ControllerError, DATABASE_FIELDS, Vault, controller_directory, run_cli


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = Vault(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def existing_pair(self):
        self.vault.directory.mkdir()
        self.vault.key.write_bytes(b"original-test-key")
        self.vault.path.write_bytes(b"original-test-ciphertext")

    def test_controller_override_and_default(self):
        with patch.dict(os.environ, {"TMS_CONTROLLER_DIR": str(self.root)}):
            self.assertEqual(controller_directory(), self.root)
        with patch.dict(os.environ):
            os.environ.pop("TMS_CONTROLLER_DIR", None)
            with patch("controller.Path.home", return_value=self.root):
                self.assertEqual(controller_directory(), self.root / ".local/share/tms-ansible")

    def test_all_helpers_reject_symlinked_and_non_regular_storage(self):
        self.vault.directory.symlink_to(self.root / "missing-directory", target_is_directory=True)
        with self.assertRaises(ControllerError):
            self.vault.exists()
        self.vault.directory.unlink()
        self.vault.directory.mkdir()
        for path in (self.vault.key, self.vault.path):
            with self.subTest(path=path.name):
                path.symlink_to(self.root / "missing-file")
                with self.assertRaises(ControllerError):
                    self.vault.exists()
                path.unlink()
                path.mkdir()
                with self.assertRaises(ControllerError):
                    self.vault.exists()
                path.rmdir()

    def test_unfinished_creation_is_rejected_before_creating_a_key(self):
        self.vault.directory.mkdir()
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                pending = self.vault.directory / "vault.new"
                if symlink:
                    pending.symlink_to(self.root / "missing-file")
                else:
                    pending.write_bytes(b"unfinished-ciphertext")
                with self.assertRaises(ControllerError):
                    self.vault.create({})
                self.assertFalse(self.vault.key.exists())
                self.assertFalse(self.vault.path.exists())
                pending.unlink()

    def test_invalid_vault_payload_is_rejected_without_rewriting_files(self):
        self.existing_pair()
        before = self.vault.path.read_bytes(), self.vault.key.read_bytes()
        for values in ([], None, {}, {name: 123 for name in DATABASE_FIELDS},
                       {name: "" for name in DATABASE_FIELDS}):
            with self.subTest(values=values), patch("controller.subprocess.run", return_value=
                    subprocess.CompletedProcess([], 0, stdout=json.dumps(values).encode())):
                with self.assertRaises(ControllerError):
                    self.vault.read(DATABASE_FIELDS)
                self.assertEqual(before, (self.vault.path.read_bytes(), self.vault.key.read_bytes()))

    def test_failed_update_preserves_original_pair_and_private_pending_file(self):
        self.existing_pair()
        before = self.vault.path.read_bytes(), self.vault.key.read_bytes()
        error = subprocess.CalledProcessError(1, "ansible-vault", output=b"test-secret-marker")
        with patch("controller.subprocess.run", side_effect=error), self.assertRaises(subprocess.CalledProcessError):
            self.vault.update({"password": "test-secret-marker"})
        self.assertEqual(before, (self.vault.path.read_bytes(), self.vault.key.read_bytes()))
        pending = self.vault.directory / "keycloak-vault.new"
        self.assertEqual(self.vault.directory.stat().st_mode & 0o777, 0o700)
        for path in (self.vault.key, self.vault.path):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(pending.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(b"test-secret-marker", pending.read_bytes())
        with self.assertRaises(ControllerError):
            self.vault.update({})

    def test_cli_failures_do_not_expose_subprocess_or_private_content(self):
        marker = "test-secret-marker"
        errors = (subprocess.CalledProcessError(1, [marker], output=marker, stderr=marker),
                  ValueError(marker), FileNotFoundError(marker))
        for error in errors:
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(SystemExit) as result:
                    run_cli(lambda: (_ for _ in ()).throw(error))
                self.assertNotIn(marker, str(result.exception))

    def test_login_only_displays_the_requested_account(self):
        spec = importlib.util.spec_from_file_location("show_login", ROOT / "scripts/show-keycloak-login.py")
        login = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(login)
        for account, field in (("tms-admin", "tms_keycloak_admin_password"),
                               ("appuser", "tms_keycloak_operator_password")):
            with self.subTest(account=account), patch.object(sys, "argv", ["show-keycloak-login.py", account]), \
                    patch.object(login.Vault, "read", return_value={field: "requested-test-password"}) as read, \
                    patch("builtins.print") as output:
                login.main()
                read.assert_called_once_with((field,))
                self.assertEqual(output.call_args_list[0].args, ("Username:", account))
                self.assertEqual(output.call_args_list[1].args, ("Password:", "requested-test-password"))
