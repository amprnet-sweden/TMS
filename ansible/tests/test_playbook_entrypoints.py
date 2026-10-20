"""Exercise actual entry-point composition without provisioning a deployment host."""
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

from test_configuration import source

ROOT = Path(__file__).resolve().parents[1]
STAGES = ('build', 'database', 'https', 'keycloak', 'backend')
ROLES = ('build_tools', 'build', 'database', 'tls', 'frontend_proxy', 'keycloak', 'backend')


def expanded(path):
    plays = []
    for play in yaml.safe_load(path.read_text()):
        imported = play.get('ansible.builtin.import_playbook')
        plays.extend(expanded(path.parent / imported) if imported else [play])
    return plays


class PlaybookEntrypointTests(unittest.TestCase):
    def test_complete_and_standalone_entrypoints_have_one_preflight(self):
        preflight = expanded(ROOT / 'preflight.yml')
        complete = expanded(ROOT / 'site.yml')
        self.assertEqual(len(complete), 6)
        self.assertEqual(complete[:1], preflight)
        self.assertTrue(complete[0]['gather_facts'])
        self.assertTrue(all(play['gather_facts'] is False for play in complete[1:]))
        for index, name in enumerate(STAGES, 1):
            with self.subTest(stage=name):
                stage = expanded(ROOT / f'{name}-stage.yml')
                self.assertEqual(len(stage), 1)
                self.assertEqual(expanded(ROOT / f'{name}.yml'), preflight + stage)
                self.assertEqual(complete[index], stage[0])

    def probe(self, entrypoint, profile='standard', privilege=True):
        with tempfile.TemporaryDirectory(prefix='tms-preflight-entrypoints-') as directory:
            root = Path(directory)
            for name in ('site.yml', 'preflight.yml', *(f'{stage}{suffix}.yml' for stage in STAGES
                                                      for suffix in ('', '-stage'))):
                shutil.copyfile(ROOT / name, root / name)
            shutil.copytree(ROOT / 'vars', root / 'vars')
            # Keep the real profile validation/resolution. Instrument target eligibility
            # and sudo here; this test measures orchestration, not a host's eligibility.
            preflight = yaml.safe_load((root / 'preflight.yml').read_text())[0]
            preflight['gather_facts'] = False
            preflight['tasks'] = preflight['tasks'][:2] + [
                {'name': 'Instrumented privilege verification', 'ansible.builtin.assert': {
                    'that': ['probe_privilege_allowed'], 'fail_msg': 'Preflight privilege gate rejected'}},
                {'name': 'Record preflight invocation', 'ansible.builtin.debug': {'msg': 'PREFLIGHT_SENTINEL'}}]
            (root / 'preflight.yml').write_text(yaml.safe_dump([preflight]))
            for role in ROLES:
                tasks = root / 'roles' / role / 'tasks'
                tasks.mkdir(parents=True)
                (tasks / 'main.yml').write_text(yaml.safe_dump([
                    {'name': 'Require preflight budgets to survive across plays', 'ansible.builtin.assert': {
                        'that': ['tms_resources == probe_expected_resources']}},
                    {'name': 'Record stage execution', 'ansible.builtin.debug': {'msg': 'STAGE_SENTINEL_' + role}}]))
            archive = root / 'source.tar'
            archive.write_bytes(b'local fixture; no application build')
            profiles = yaml.safe_load((ROOT / 'vars/resources.yml').read_text())['tms_resource_profiles']
            values = {
                'ansible_python_interpreter': sys.executable, 'ansible_become': False,
                'probe_privilege_allowed': privilege, 'probe_expected_resources': profiles.get(profile, {}),
                'tms_resource_profile': profile, 'tms_public_origin': 'https://service.example.test',
                'tms_source_archive': str(archive), 'tms_source_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'tms_build_recipe_sha256': 'a' * 64, 'tms_source_base_commit': 'b' * 40,
                'tms_database_deployment_id': 'c' * 32, 'tms_tls_source_directory': str(root),
                'tms_tls_ca_sha256': 'd' * 64,
            }
            for index, field in enumerate(('database', 'keycloak_database', 'keycloak_bootstrap',
                                           'keycloak_admin', 'keycloak_lookup', 'keycloak_operator')):
                values['tms_' + field + '_password'] = chr(ord('a') + index) * 48
            inventory = root / 'inventory.yml'
            inventory.write_text('all:\n  children:\n    tms:\n      hosts:\n        localhost:\n          ansible_connection: local\n')
            env = dict(os.environ, PYTHONUNBUFFERED='1', ANSIBLE_STDOUT_CALLBACK='default', ANSIBLE_NOCOLOR='1',
                       ANSIBLE_LOCAL_TEMP=str(root / 'local'), ANSIBLE_REMOTE_TEMP=str(root / 'remote'))
            env.pop('ANSIBLE_CALLBACKS_ENABLED', None)
            return subprocess.run([str(Path(sys.executable).parent / 'ansible-playbook'), '-i', str(inventory),
                                   str(root / entrypoint), '-e', json.dumps(values)], env=env,
                                  capture_output=True, text=True, timeout=45)

    def test_full_execution_runs_preflight_once_and_shares_budgets_for_both_profiles(self):
        for profile in ('standard', 'pi_1gb_experimental'):
            with self.subTest(profile=profile):
                result = self.probe('site.yml', profile)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stdout.count('PREFLIGHT_SENTINEL'), 1)
                positions = [result.stdout.index('STAGE_SENTINEL_' + role + '"') for role in ROLES]
                self.assertEqual(positions, sorted(positions))
                self.assertIn('changed=0', result.stdout)

    def test_standalone_execution_retains_preflight_and_expected_roles(self):
        for stage, roles in zip(STAGES, (('build_tools', 'build'), ('database',),
                                        ('tls', 'frontend_proxy'), ('keycloak',), ('backend',))):
            with self.subTest(stage=stage):
                result = self.probe(stage + '.yml')
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(result.stdout.count('PREFLIGHT_SENTINEL'), 1)
                self.assertEqual(result.stdout.count('STAGE_SENTINEL_'), len(roles))
                self.assertLess(result.stdout.index('PREFLIGHT_SENTINEL'), result.stdout.index('STAGE_SENTINEL_'))

    def test_invalid_profile_and_rejected_preflight_prevent_all_stages(self):
        for profile, privilege in (('unsupported', True), ('standard', False)):
            with self.subTest(profile=profile, privilege=privilege):
                result = self.probe('site.yml', profile, privilege)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertNotIn('STAGE_SENTINEL_', result.stdout)

    def test_extracted_build_stage_is_part_of_the_actual_recipe_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ansible = root / 'ansible'
            (ansible / 'scripts').mkdir(parents=True)
            for name in ('build.yml', 'build-stage.yml', 'scripts/prepare-source.py'):
                shutil.copyfile(ROOT / name, ansible / name)
            shutil.copytree(ROOT / 'vars', ansible / 'vars')
            for role in ('build', 'build_tools'):
                shutil.copytree(ROOT / 'roles' / role, ansible / 'roles' / role)
            (root / 'backend').mkdir()
            (root / 'backend/build.gradle').write_text('JavaLanguageVersion.of(25)\n')
            (root / 'backend/gradlew').write_text('#!/bin/sh\n')
            (root / 'frontend').mkdir()
            (root / 'frontend/package.json').write_text('{}')
            (root / 'frontend/package-lock.json').write_text('{"packages":{"":{}}}')

            def git(root, *arguments):
                if arguments[0] == 'rev-parse':
                    return b'0' * 40
                return b'100644 0000 0\tbackend/build.gradle\0'

            with patch.object(source, '__file__', str(ansible / 'scripts/prepare-source.py')), \
                    patch.object(source, 'git', git), redirect_stdout(io.StringIO()):
                source.main()
                before = json.loads((ansible / '.local/source-vars.json').read_text())
                with (ansible / 'build-stage.yml').open('a') as stage:
                    stage.write('\n# Changed build instruction\n')
                source.main()
                after = json.loads((ansible / '.local/source-vars.json').read_text())
            self.assertEqual(before['tms_source_sha256'], after['tms_source_sha256'])
            self.assertNotEqual(before['tms_build_recipe_sha256'], after['tms_build_recipe_sha256'])
