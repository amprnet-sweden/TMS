"""Run controller CLIs in an isolated checkout; never provision a deployment host."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from controller import DATABASE_FIELDS, Vault
from deployment import load


class ControllerWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tms-controller-workflow-")
        self.root = Path(self.temp.name)
        self.checkout = self.root / "installer"
        shutil.copytree(ROOT / "scripts", self.checkout / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(ROOT / "install.sh", self.checkout / "install.sh")
        self.controller = self.root / "controller"
        self.local = self.checkout / ".local"
        self.config = self.root / "deployment.json"
        self.config.write_text(json.dumps({"tms_public_origin": "https://service.example.test:9443",
                                          "tms_tenant": "test-tenant", "tms_resource_profile": "pi_1gb_experimental"}))
        self.env = dict(os.environ, TMS_CONTROLLER_DIR=str(self.controller))

    def tearDown(self):
        self.temp.cleanup()

    def run_helper(self, name):
        return subprocess.run([sys.executable, str(self.checkout / "scripts" / name), str(self.config)],
                              env=self.env, capture_output=True, text=True)

    def test_deployment_variables_do_not_require_tls_or_a_vault(self):
        for profile in ("standard", "pi_1gb_experimental"):
            values = json.loads(self.config.read_text())
            values["tms_resource_profile"] = profile
            self.config.write_text(json.dumps(values))
            result = self.run_helper("prepare-deployment.py")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((self.local / "deployment-vars.json").read_text()), load(self.config))
            self.assertFalse(self.controller.exists())
            self.assertFalse((self.local / "tls-vars.json").exists())

    def test_tls_exports_only_certificate_variables_and_preserves_settings_on_failure(self):
        self.assertEqual(self.run_helper("prepare-deployment.py").returncode, 0)
        before = (self.local / "deployment-vars.json").read_bytes()
        self.assertEqual(self.run_helper("prepare-tls.py").returncode, 0)
        tls = json.loads((self.local / "tls-vars.json").read_text())
        self.assertEqual(set(tls), {"tms_tls_source_directory", "tms_tls_ca_sha256",
                                    "tms_tls_ca_der_sha256", "tms_tls_server_expires"})
        self.assertEqual(tls["tms_tls_source_directory"], str(self.controller / "tls"))
        hashes = {p.name: p.read_bytes() for p in (self.controller / "tls").iterdir()}
        exported = (self.local / "tls-vars.json").read_bytes()
        self.assertEqual(self.run_helper("prepare-tls.py").returncode, 0)
        self.assertEqual(exported, (self.local / "tls-vars.json").read_bytes())
        self.assertEqual(hashes, {p.name: p.read_bytes() for p in (self.controller / "tls").iterdir()})
        (self.controller / "tls/server.key").unlink()
        remaining = {p.name: p.read_bytes() for p in (self.controller / "tls").iterdir()}
        self.assertNotEqual(self.run_helper("prepare-tls.py").returncode, 0)
        self.assertEqual(before, (self.local / "deployment-vars.json").read_bytes())
        self.assertEqual(remaining, {p.name: p.read_bytes() for p in (self.controller / "tls").iterdir()})

    def executable(self, name, body):
        path = self.controller / "venv/bin" / name
        path.write_text(f"#!{sys.executable}\n" + body)
        path.chmod(0o700)

    def test_installer_passes_separate_variables_and_reuses_original_credentials(self):
        # Stub only target commands and application source packing. Run real controller
        # preparation, TLS generation and Ansible vault encryption in temporary storage.
        binary = self.controller / "venv/bin"
        binary.mkdir(parents=True)
        (binary / "ansible-vault").symlink_to(Path(sys.executable).parent / "ansible-vault")
        self.executable("python", f'''
import os
from pathlib import Path
import sys
if Path(sys.argv[1]).name == "prepare-source.py":
    (Path(sys.argv[1]).parents[1] / ".local/source-vars.json").write_text('{{}}')
else:
    os.execv({sys.executable!r}, [{sys.executable!r}, *sys.argv[1:]])
''')
        self.executable("ansible-galaxy", "# Collection installation is covered by the syntax checks.\n")
        self.executable("ansible-playbook", '''
import json
from pathlib import Path
import sys
files = [Path(value[1:]) for index, value in enumerate(sys.argv) if index and sys.argv[index-1] == '--extra-vars']
assert {p.name for p in files} == {'source-vars.json', 'deployment-vars.json', 'tls-vars.json', 'vault.yml'}
values = {}
for path in files:
    if path.name != 'vault.yml':
        values.update(json.loads(path.read_text()))
assert values['tms_public_origin'] == 'https://service.example.test:9443'
assert values['tms_hostname'] == 'service.example.test'
assert values['tms_https_port'] == 9443
assert values['tms_tenant'] == 'test-tenant'
assert values['tms_resource_profile'] == 'pi_1gb_experimental'
assert Path(values['tms_tls_source_directory'], 'ca.crt').is_file()
(files[0].parent / 'playbook-invoked').touch()
''')
        inventory = self.root / "inventory.yml"
        inventory.write_text("all: {}\n")
        command = ["bash", str(self.checkout / "install.sh"), str(inventory), str(self.config)]
        result = subprocess.run(command, env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertTrue((self.local / "playbook-invoked").is_file())
        vault = Vault(self.controller)
        values = vault.read(DATABASE_FIELDS)
        self.assertEqual(len(values), 7)
        before = {p.name: p.read_bytes() for directory in (vault.directory, self.controller / "tls") for p in directory.iterdir()}
        result = subprocess.run(command, env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(before, {p.name: p.read_bytes() for directory in (vault.directory, self.controller / "tls") for p in directory.iterdir()})
        for secret in values.values():
            self.assertNotIn(secret.encode(), result.stdout + result.stderr)
        (self.local / "playbook-invoked").unlink()
        self.config.write_text('{"tms_public_origin": false}')
        result = subprocess.run(command, env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.local / "playbook-invoked").exists())
        self.assertEqual(before, {p.name: p.read_bytes() for directory in (vault.directory, self.controller / "tls") for p in directory.iterdir()})
