"""Check opt-in eligibility and actual service/build budgets for both profiles."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deployment import load


class ResourceTests(unittest.TestCase):
    def configuration(self, **extra):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'deployment.json'
            path.write_text(json.dumps(dict(tms_public_origin='https://service.example.test', **extra)))
            return load(path)

    def test_existing_configuration_keeps_standard_profile(self):
        self.assertEqual(self.configuration()['tms_resource_profile'], 'standard')

    def test_small_profile_is_explicit_and_unknown_profiles_are_rejected(self):
        self.assertEqual(self.configuration(tms_resource_profile='pi_1gb_experimental')['tms_resource_profile'],
                         'pi_1gb_experimental')
        for value in ('tiny', '', None, [], 1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.configuration(tms_resource_profile=value)

    def test_service_and_database_templates_obey_each_profile(self):
        profiles = yaml.safe_load((ROOT / 'vars/resources.yml').read_text())['tms_resource_profiles']
        environment = Environment(undefined=StrictUndefined)
        for profile, maximum, minimum in (('standard', 768, 3500), ('pi_1gb_experimental', 256, 850)):
            resources = profiles[profile]
            self.assertEqual(resources['minimum_memory_mb'], minimum)
            values = dict(tms_resources=resources, tms_resource_profile=profile,
                          tms_java_home='/java', tms_keycloak_home='/keycloak')
            for role, filename in (('backend', 'tms-backend.service.j2'), ('keycloak', 'tms-keycloak.service.j2')):
                template = environment.from_string((ROOT / f'roles/{role}/templates/{filename}').read_text())
                self.assertIn(f'-Xmx{maximum}m', template.render(**values))
            database = environment.from_string((ROOT / 'roles/database/templates/native.cnf.j2').read_text()).render(**values)
            self.assertEqual('innodb-buffer-pool-size = 64M' in database, profile == 'pi_1gb_experimental')
            self.assertIn('bind-address = 127.0.0.1', database)

    def test_build_budgets_affect_artifact_fingerprints(self):
        profiles = yaml.safe_load((ROOT / 'vars/resources.yml').read_text())['tms_resource_profiles']
        task = yaml.safe_load((ROOT / 'roles/build/tasks/main.yml').read_text())[0]
        environment = Environment(undefined=StrictUndefined)
        environment.filters['to_json'] = json.dumps
        environment.filters['hash'] = lambda value, algorithm: hashlib.new(algorithm, value.encode()).hexdigest()
        values = dict(tms_source_sha256='source', tms_build_recipe_sha256='recipe',
                      build_tools_java_version={'stderr': 'java21'},
                      build_tools_compiler_version={'stdout': 'javac21'},
                      tms_backend_tests='skipped', tms_node_sha256='node',
                      tms_public_origin='https://service.example.test')
        for expression in task['ansible.builtin.set_fact'].values():
            template = environment.from_string(expression)
            standard = template.render(**values, tms_resources=profiles['standard'])
            small = template.render(**values, tms_resources=profiles['pi_1gb_experimental'])
            self.assertNotEqual(standard, small)
