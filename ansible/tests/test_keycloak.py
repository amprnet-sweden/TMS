"""Test credential migration and identity safety without changing the lab VM."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("identity", ROOT / "roles/keycloak/files/configure-keycloak.py")
identity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(identity)


class RealmTests(unittest.TestCase):
    def test_client_url_order_does_not_trigger_an_update(self):
        desired = {"redirectUris": ["https://example.test/tms", "https://example.test/tms/*"],
                   "webOrigins": ["https://example.test", "https://second.test"], "publicClient": True}
        current = {**desired, "redirectUris": list(reversed(desired["redirectUris"])),
                   "webOrigins": list(reversed(desired["webOrigins"]))}
        self.assertFalse(identity.client_needs_update(current, desired))
        for field in ("redirectUris", "webOrigins"):
            self.assertTrue(identity.client_needs_update({**current, field: current[field][1:]}, desired))
            self.assertTrue(identity.client_needs_update({**current, field: current[field] + ["https://unexpected.test"]}, desired))
        self.assertTrue(identity.client_needs_update({**current, "publicClient": False}, desired))

    def test_lookup_permissions_include_keycloak_composite_read_roles(self):
        identity.verify_lookup_roles([
            {"name": name} for name in ("view-users", "query-users", "query-groups")])

    def test_lookup_permissions_reject_management_or_missing_roles(self):
        for names in (("view-users", "query-users", "query-groups", "manage-users"),
                      ("query-users", "query-groups")):
            with self.subTest(names=names), self.assertRaisesRegex(RuntimeError, "unexpected realm permissions"):
                identity.verify_lookup_roles([{"name": name} for name in names])

    def test_import_sanitizes_privileges_and_urls_without_modifying_source(self):
        source = json.loads((ROOT.parent / "docker/keycloak/amprnet-realm.json").read_text())
        before = json.dumps(source)
        desired = identity.realm_settings(source, "https://tms.example.test:8443")
        self.assertEqual(json.dumps(source), before)
        self.assertFalse(desired["registrationAllowed"])
        self.assertTrue(desired["bruteForceProtected"])
        defaults = next(r for r in desired["roles"]["realm"] if r["name"] == "default-roles-amprnet")
        self.assertNotIn("tms-superuser", defaults["composites"]["realm"])
        web = next(c for c in desired["clients"] if c["clientId"] == "tms-web-app")
        self.assertEqual(web["webOrigins"], ["https://tms.example.test:8443"])
        self.assertFalse(web["directAccessGrantsEnabled"])
        cli = next(c for c in desired["clients"] if c["clientId"] == "admin-cli")
        self.assertEqual(cli["attributes"]["client.use.lightweight.access.token.enabled"], "false")
        self.assertTrue(all("secret" not in c for c in desired["clients"]))

    def test_existing_user_password_is_never_updated(self):
        client = identity.Identity.__new__(identity.Identity)
        client.values = {"deployment_id": "test-deployment"}
        client.api = Mock(return_value=[{"id": "user-id", "attributes": {"tms-managed-by": ["test-deployment"]}}])
        self.assertEqual(client.user("master", "tms-admin", "unused-password"), "user-id")
        self.assertTrue(all(call.args[0] == "GET" for call in client.api.call_args_list))

    def test_unmanaged_same_name_user_is_rejected_without_changes(self):
        client = identity.Identity.__new__(identity.Identity)
        client.values = {"deployment_id": "test-deployment"}
        client.api = Mock(return_value=[{"id": "unrelated-user"}])
        with self.assertRaisesRegex(RuntimeError, "unmanaged"):
            client.user("master", "tms-admin", "unused-password")
        self.assertTrue(all(call.args[0] == "GET" for call in client.api.call_args_list))


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tms-keycloak-test-")
        self.root = Path(self.temp.name)
        (self.root / "venv").symlink_to(Path(sys.executable).parent.parent)
        self.env = dict(os.environ, TMS_CONTROLLER_DIR=str(self.root))
        self.run_script("prepare-database-vault.py")

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, name):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        return result

    def decrypt(self):
        return json.loads(subprocess.run([str(self.root / "venv/bin/ansible-vault"), "view",
            "--vault-password-file", str(self.root / "secrets/vault.key"),
            str(self.root / "secrets/vault.yml")], capture_output=True, check=True).stdout)

    def test_extension_preserves_credentials_and_ciphertext_on_rerun(self):
        original = self.decrypt()
        result = self.run_script("prepare-keycloak-vault.py")
        updated = self.decrypt()
        self.assertTrue(original.items() <= updated.items())
        self.assertEqual(len(updated), len(original) + 4)
        vault = self.root / "secrets/vault.yml"
        ciphertext = vault.read_bytes()
        self.assertTrue(ciphertext.startswith(b"$ANSIBLE_VAULT;"))
        self.assertEqual(vault.stat().st_mode & 0o777, 0o600)
        for secret in updated.values():
            self.assertNotIn(secret.encode(), result.stdout + result.stderr + ciphertext)
        self.run_script("prepare-keycloak-vault.py")
        self.assertEqual(vault.read_bytes(), ciphertext)

    def test_partial_credentials_are_not_replaced(self):
        values = self.decrypt()
        values["tms_keycloak_admin_password"] = "previous-password"
        vault = self.root / "secrets/vault.yml"
        vault.unlink()
        subprocess.run([str(self.root / "venv/bin/ansible-vault"), "encrypt", "--vault-password-file",
            str(self.root / "secrets/vault.key"), "--output", str(vault), "-"],
            input=json.dumps(values).encode(), capture_output=True, check=True)
        before = vault.read_bytes()
        result = subprocess.run([sys.executable, str(ROOT / "scripts/prepare-keycloak-vault.py")],
                                env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(vault.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
