"""Exercise the emitted build report and the actual shared Ansible assertions."""
import copy
import unittest

from ansible.template import Templar

import test_configuration as configuration


class BuildReportTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration.ConfigurationTests()
        self.config.setUp()
        self.root = '/custom/build.[1]'
        self.backend = 'a' * 64
        self.frontend = 'b' * 64
        self.origin = 'https://service.example.test:8443'
        self.backend_path = f'{self.root}/backend/{self.backend}/backend/app.jar'
        self.frontend_path = f'{self.root}/frontend/{self.frontend}/frontend/dist'
        producer = next(t for t in self.config.tasks('build') if t['name'] == 'Write the build report without secrets')
        self.report = self.config.render(
            producer['vars']['build_report'], tms_build_root=self.root,
            build_backend_fingerprint=self.backend, build_frontend_fingerprint=self.frontend,
            tms_resource_profile='standard', tms_resources={}, tms_source_base_commit='c' * 40,
            tms_source_sha256='d' * 64, tms_build_recipe_sha256='e' * 64,
            build_tools_java_version={'stderr': 'openjdk 25'},
            build_tools_compiler_version={'stdout': 'javac 25'},
            build_tools_node_version={'stdout': 'v22.22.0'}, tms_public_origin=self.origin,
            tms_backend_tests='skipped',
            build_backend_artifact={'stat': {'path': self.backend_path, 'checksum': 'f' * 64}},
            build_frontend_artifacts={'files': [
                {'path': self.frontend_path + '/index.html', 'checksum': '1' * 64},
                {'path': self.frontend_path + '/assets/app.js', 'checksum': '2' * 64}]})
        self.checks = configuration.trusted(self.config.loader.load_from_file(
            str(configuration.ROOT / 'tasks/validate-build-report.yml')))

    def accepted(self, report):
        values = dict(tms_build_report=report, tms_build_root=self.root, tms_public_origin=self.origin)
        for task in self.checks:
            templar = Templar(loader=self.config.loader, variables=values)
            items = templar.template(task['loop']) if 'loop' in task else [None]
            for item in items:
                if not self.config.allowed(task, **values, item=item):
                    return False
        return True

    def test_producer_report_is_accepted_and_release_uses_fingerprint(self):
        self.assertTrue(self.accepted(self.report))
        self.assertEqual(self.report['schema_version'], 1)
        task = next(t for t in self.config.tasks('frontend_proxy')
                    if t['name'] == 'Derive the immutable frontend release directory')
        self.assertEqual(self.config.render(task['ansible.builtin.set_fact']['frontend_proxy_release'],
                                           frontend_proxy_build=self.report),
                         '/srv/tms/releases/' + self.frontend)

    def test_each_consumer_validates_before_artifact_access(self):
        for role, variable in (('backend', 'backend_build'), ('frontend_proxy', 'frontend_proxy_build')):
            tasks = self.config.tasks(role)
            validation = next(i for i, t in enumerate(tasks) if t['name'] == 'Require a versioned build report')
            access = next(i for i, t in enumerate(tasks)
                          if 'ansible.builtin.stat' in t or 'ansible.builtin.find' in t)
            self.assertLess(validation, access)
            imports = self.config.loader.load_from_file(str(configuration.ROOT / f'roles/{role}/tasks/validate.yml'))
            contract = next(t for t in imports if 'ansible.builtin.import_tasks' in t)
            self.assertEqual(self.config.render(configuration.trusted(contract['vars']['tms_build_report']),
                                               **{variable: self.report}), self.report)

    def test_missing_required_fields_are_rejected(self):
        for field in ('schema_version', 'source_base_commit', 'source_sha256', 'recipe_sha256',
                      'public_origin', 'backend_fingerprint', 'frontend_fingerprint', 'backend_jar',
                      'backend_sha256', 'frontend_directory', 'frontend_files'):
            with self.subTest(field=field):
                report = copy.deepcopy(self.report)
                del report[field]
                self.assertFalse(self.accepted(report))

    def test_unknown_or_malformed_schema_is_rejected(self):
        for value in (0, 2, '1', True, None, [], {}):
            with self.subTest(value=value):
                self.assertFalse(self.accepted({**self.report, 'schema_version': value}))
        for value in (None, [], 'report', 1):
            with self.subTest(report=value):
                self.assertFalse(self.accepted(value))

    def test_invalid_field_types_and_digests_are_rejected(self):
        for field in ('source_base_commit', 'source_sha256', 'recipe_sha256', 'public_origin',
                      'backend_fingerprint', 'frontend_fingerprint', 'backend_jar',
                      'backend_sha256', 'frontend_directory'):
            for value in (None, [], {}, 1, ''):
                with self.subTest(field=field, value=value):
                    self.assertFalse(self.accepted({**self.report, field: value}))
        for field in ('source_sha256', 'recipe_sha256', 'backend_fingerprint',
                      'frontend_fingerprint', 'backend_sha256'):
            for value in ('a' * 63, 'g' * 64, 'A' * 64, '../' + 'a' * 64):
                with self.subTest(field=field, value=value):
                    self.assertFalse(self.accepted({**self.report, field: value}))

    def test_mismatched_paths_origin_and_provenance_are_rejected(self):
        for field, value in (
                ('source_base_commit', 'c' * 39), ('public_origin', 'https://other.example.test'),
                ('backend_fingerprint', '3' * 64), ('frontend_fingerprint', '3' * 64),
                ('backend_jar', self.backend_path.replace(self.root, '/custom/buildX1')),
                ('frontend_directory', self.frontend_path + '/..'),
                ('backend_jar', '/tmp/app.jar')):
            with self.subTest(field=field, value=value):
                self.assertFalse(self.accepted({**self.report, field: value}))

    def test_invalid_manifests_are_rejected(self):
        index = self.frontend_path + '/index.html'
        for manifest in (None, [], {}, 'files', {index: 'bad'}, {index: 123},
                         {index: '1' * 64, '/tmp/extra': '2' * 64},
                         {index: '1' * 64, self.frontend_path + '/../extra': '2' * 64},
                         {index: '1' * 64, self.frontend_path + '/assets/./app.js': '2' * 64},
                         {self.frontend_path + '/assets/app.js': '2' * 64}):
            with self.subTest(manifest=manifest):
                self.assertFalse(self.accepted({**self.report, 'frontend_files': manifest}))


if __name__ == '__main__':
    unittest.main()
