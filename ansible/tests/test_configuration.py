"""Check real Ansible expressions for toolchains, paths and ownership guards."""
import importlib.util
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar, trust_as_template

ROOT = Path(__file__).resolve().parents[1]
init_plugin_loader()


def helper(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


source = helper('source_preparation', 'scripts/prepare-source.py')
backend = helper('backend_probe', 'roles/backend/files/verify-backend.py')


def trusted(value):
    # These inputs are repository configuration, just as in a playbook run.
    if isinstance(value, str):
        return trust_as_template(value)
    if isinstance(value, dict):
        return {key: trusted(item) for key, item in value.items()}
    if isinstance(value, list):
        return [trusted(item) for item in value]
    return value


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.loader = DataLoader()
        self.values = {}
        for filename in ('common', 'build'):
            self.values.update(trusted(self.loader.load_from_file(str(ROOT / f'vars/{filename}.yml'))))

    def tasks(self, role):
        def load(path):
            tasks = []
            for task in self.loader.load_from_file(str(path)):
                imported = task.get('ansible.builtin.import_tasks')
                if imported:
                    tasks.extend(load(path.parent / imported))
                else:
                    tasks.append(task)
            return tasks

        return trusted(load(ROOT / f'roles/{role}/tasks/main.yml'))

    def render(self, value, **extra):
        return Templar(loader=self.loader, variables={**self.values, **extra}).template(value)

    def allowed(self, task, **extra):
        templar = Templar(loader=self.loader, variables={**self.values, **extra})
        return all(templar.evaluate_expression(condition) for condition in task['ansible.builtin.assert']['that'])

    def test_java_pin_controls_package_home_and_checks(self):
        checks = next(t for t in self.tasks('build_tools') if t['name'] == 'Require the selected Java and Node versions')
        for version in (21, 25):
            values = dict(tms_java_version=version,
                          build_tools_compiler_version={'stdout': f'javac {version}.0.1'},
                          build_tools_java_version={'stderr': f'openjdk version "{version}.0.1"'},
                          build_tools_node_version={'stdout': 'v' + self.values['tms_node_version']})
            self.assertEqual(self.render(self.values['tms_java_package'], **values), f'openjdk-{version}-jdk-headless')
            self.assertEqual(self.render(self.values['tms_java_home'], **values), f'/usr/lib/jvm/java-{version}-openjdk-arm64')
            self.assertTrue(self.allowed(checks, **values))
            values['build_tools_compiler_version'] = {'stdout': 'javac 17.0.1'}
            self.assertFalse(self.allowed(checks, **values))
            source.require_java_version(f'JavaLanguageVersion.of({version})', version)
            with self.assertRaises(SystemExit):
                source.require_java_version('JavaLanguageVersion.of(17)', version)
        source.require_java_version((ROOT.parent / 'backend/build.gradle').read_text(), self.values['tms_java_version'])

    def test_custom_build_root_is_escaped_in_artifact_checks(self):
        build_root = '/custom/build.[1]'
        digest = 'a' * 64
        for role, key, artifact in (
                ('backend', 'backend_build', f'backend/{digest}/backend/app.jar'),
                ('frontend_proxy', 'frontend_proxy_build', f'frontend/{digest}/frontend/dist')):
            task = next(t for t in self.tasks(role) if t['name'].startswith('Require ') and
                        any('regex_escape' in c for c in t.get('ansible.builtin.assert', {}).get('that', [])))
            condition = next(c for c in task['ansible.builtin.assert']['that'] if 'regex_escape' in c)
            field = 'backend_jar' if role == 'backend' else 'frontend_directory'
            templar = Templar(variables={'tms_build_root': build_root, key: {field: f'{build_root}/{artifact}'}})
            self.assertTrue(templar.evaluate_expression(condition))
            templar = Templar(variables={'tms_build_root': build_root, key: {field: f'/custom/buildX1/{artifact}'}})
            self.assertFalse(templar.evaluate_expression(condition))

    def test_shared_state_paths_reach_services_and_helpers(self):
        values = dict(tms_database_state_directory='/custom/state', tms_build_root='/custom/build',
                      tms_build_cache_directory='/custom/cache', tms_database_socket='/custom/mysql.sock',
                      tms_java_home='/custom/java', tms_backend_trust_store='/custom/cacerts',
                      tms_public_origin='https://service.example.test', tms_keycloak_operator_password='test')
        tasks = self.tasks('backend')
        inputs = next(t for t in tasks if t.get('register') == 'backend_inputs_inspection')
        self.assertEqual(self.render(inputs['loop'], **values)[0]['path'], '/custom/build/build-report.json')
        query = next(t for t in tasks if 'ansible.mariadb.mariadb_query' in t)
        self.assertEqual(self.render(query['ansible.mariadb.mariadb_query']['login_unix_socket'], **values), '/custom/mysql.sock')
        check = next(t for t in tasks if t.get('register') == 'backend_verification')
        payload = self.render(check['ansible.builtin.command']['stdin'], **values)
        payload = json.loads(payload)
        self.assertEqual(payload['ca_file'], '/custom/state/tls/ca.crt')
        self.assertEqual(payload['java_executable'], '/custom/java/bin/java')
        self.assertEqual(payload['trust_store'], '/custom/cacerts')

    def test_named_inspections_are_independent_of_loop_order(self):
        for role in ('backend', 'keycloak', 'database', 'build_tools'):
            for task in self.tasks(role):
                if not task['name'].startswith('Index '):
                    continue
                key, expression = next(iter(task['ansible.builtin.set_fact'].items()))
                field = 'content' if key == 'backend_inputs' else 'stat'
                results = [{'item': {'name': name}, field: {'exists': exists}}
                           for name, exists in (('owner', False), ('ready', True))]
                expected = {'owner': {'exists': False}, 'ready': {'exists': True}}
                for ordered in (results, list(reversed(results))):
                    self.assertEqual(self.render(expression, **{key + '_inspection': {'results': ordered}}), expected)

    def test_ownership_guards_keep_fresh_managed_and_unmanaged_behavior(self):
        cases = (
            ('build_tools', 'Refuse to adopt an unmanaged build directory', 'build_tools_directory_state',
             ['root', 'marker'], 'marker', ['root'], {}, []),
            ('database', 'Refuse to adopt an unmanaged database installation', 'database_existing',
             ['owner', 'data', 'ready'], 'owner', ['data'], {'packages': {}}, []),
            ('keycloak', 'Require completed prerequisites and refuse unmanaged Keycloak', 'keycloak_paths',
             ['database_ready', 'https_ca', 'owner', 'installation', 'service', 'ready'], 'owner',
             ['installation', 'service'], {'getent_passwd': {'keycloak': None}}, ['database_ready', 'https_ca']),
            ('backend', 'Require Java trust and refuse an unmanaged backend installation', 'backend_paths',
             ['owner', 'installation', 'configuration', 'data', 'service', 'trust_store'], 'owner',
             ['installation', 'configuration', 'data', 'service'], {'getent_passwd': {'tms-backend': None}}, []),
        )
        for role, name, key, names, owner, unmanaged, facts, prerequisites in cases:
            task = next(t for t in self.tasks(role) if t['name'] == name)
            paths = {n: {'exists': n in prerequisites, 'isreg': n == 'trust_store'} for n in names}
            with self.subTest(role=role):
                self.assertTrue(self.allowed(task, **{key: paths, 'ansible_facts': facts}))
                for path in unmanaged:
                    paths[path]['exists'] = True
                    self.assertFalse(self.allowed(task, **{key: paths, 'ansible_facts': facts}))
                    paths[path]['exists'] = False
                for path in unmanaged:
                    paths[path]['exists'] = True
                paths[owner]['exists'] = True
                self.assertTrue(self.allowed(task, **{key: paths, 'ansible_facts': facts}))
                for prerequisite in prerequisites:
                    paths[prerequisite]['exists'] = False
                    self.assertFalse(self.allowed(task, **{key: paths, 'ansible_facts': facts}))
                    paths[prerequisite]['exists'] = True

    def test_websocket_probe_uses_supplied_java_and_trust_store(self):
        with patch.object(backend.subprocess, 'run', return_value=Mock(returncode=0, stdout='STOMP CONNECTED')) as run:
            backend.websocket_check('https://service.example.test', 'test-token', '/custom/java/bin/java', '/custom/cacerts')
        argv = run.call_args.args[0]
        self.assertEqual(argv[0], '/custom/java/bin/java')
        self.assertIn('-Djavax.net.ssl.trustStore=/custom/cacerts', argv)
        self.assertNotIn('test-token', argv)

    def test_tls_rejects_unmanaged_nginx_and_ca_replacement(self):
        tasks = self.tasks('tls')
        ownership = next(t for t in tasks if t['name'] == 'Refuse to adopt an unmanaged NGINX installation')
        for managed in (False, True):
            for installed in (False, True):
                with self.subTest(managed=managed, installed=installed):
                    self.assertEqual(self.allowed(
                        ownership, tls_marker={'stat': {'exists': managed}},
                        ansible_facts={'packages': {'nginx': []} if installed else {}}),
                        managed or not installed)

        pin = next(t for t in tasks if t['name'] == 'Reject unintended CA replacement')
        original = 'a' * 64
        saved = {'content': base64.b64encode((original + '\n').encode()).decode()}
        self.assertTrue(self.allowed(pin, tls_original_ca=saved, tms_tls_ca_sha256=original))
        self.assertFalse(self.allowed(pin, tls_original_ca=saved, tms_tls_ca_sha256='b' * 64))

    def test_tls_checks_the_existing_java_trust_anchor(self):
        check = next(t for t in self.tasks('tls') if t['name'] == 'Require the expected CA in the backend trust store')
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'ca.crt').write_text('-----BEGIN CERTIFICATE-----\nexpected\n-----END CERTIFICATE-----\n')
            values = dict(tms_tls_source_directory=directory)
            self.assertTrue(self.allowed(check, **values, tls_exported_ca={
                'stdout': '-----BEGIN CERTIFICATE-----\nexpected\n-----END CERTIFICATE-----'}))
            self.assertFalse(self.allowed(check, **values, tls_exported_ca={
                'stdout': '-----BEGIN CERTIFICATE-----\nother\n-----END CERTIFICATE-----'}))
