"""Evaluate the actual stage credential guards and password JSON transport."""
import json
import unittest

from ansible.template import Templar
import test_configuration as configuration


class LoginPasswordTests(unittest.TestCase):
    def setUp(self):
        self.config = configuration.ConfigurationTests()
        self.config.setUp()

    def guards(self, stage):
        play = configuration.trusted(self.config.loader.load_from_file(str(configuration.ROOT / f'{stage}-stage.yml'))[0])
        return play['pre_tasks']

    def allowed(self, task, values):
        templar = Templar(loader=self.config.loader, variables=values)
        items = templar.template(task['loop']) if 'loop' in task else [None]
        for item in items:
            current = Templar(loader=self.config.loader, variables={**values, 'item': item})
            if not all(current.evaluate_expression(c) for c in task['ansible.builtin.assert']['that']):
                return False
        return True

    def values(self, password):
        return dict(ansible_check_mode=False, tms_public_origin='https://tms.example.test',
                    tms_database_deployment_id='a' * 32, tms_database_password='b' * 48,
                    tms_keycloak_database_password='c' * 48, tms_keycloak_bootstrap_password='d' * 48,
                    tms_keycloak_lookup_password='e' * 48,
                    tms_keycloak_admin_password=password, tms_keycloak_operator_password=password)

    def test_existing_login_passwords_accept_short_special_unicode_and_whitespace(self):
        for password in ('x', 'short', 'p@ss: "word" \\ $!', 'lösenord 🔑', ' leading and trailing ', 'line\nbreak'):
            for stage in ('keycloak', 'backend'):
                with self.subTest(stage=stage, password=password):
                    self.assertTrue(all(self.allowed(t, self.values(password)) for t in self.guards(stage)))

    def test_empty_and_nonstring_login_passwords_are_rejected_without_logging(self):
        for stage in ('keycloak', 'backend'):
            guard = self.guards(stage)[1]
            self.assertTrue(guard['no_log'])
            for password in ('', None, False, 123, [], {}):
                with self.subTest(stage=stage, kind=type(password).__name__):
                    self.assertFalse(self.allowed(guard, self.values(password)))
            fields = ('tms_keycloak_admin_password', 'tms_keycloak_operator_password') if stage == 'keycloak' else ('tms_keycloak_operator_password',)
            for field in fields:
                values = self.values('valid')
                values[field] = ''
                self.assertFalse(self.allowed(guard, values))

    def test_generated_service_credential_guards_remain_in_force(self):
        for stage, fields in (
                ('keycloak', ('tms_keycloak_database_password', 'tms_keycloak_bootstrap_password', 'tms_keycloak_lookup_password')),
                ('backend', ('tms_database_password', 'tms_keycloak_lookup_password'))):
            guard = self.guards(stage)[0]
            self.assertTrue(guard['no_log'])
            for field in fields:
                for password in ('', 'short', 'a' * 32 + '!'):
                    with self.subTest(stage=stage, field=field):
                        values = self.values('human-password!')
                        values[field] = password
                        self.assertFalse(self.allowed(guard, values))

    def test_special_login_passwords_reach_helpers_unchanged_as_json(self):
        password = '短い "quoted" \\ password\nwith whitespace'
        values = dict(self.values(password), tms_tls_directory='/etc/tms/tls',
                      tms_java_home='/java', tms_backend_trust_store='/cacerts',
                      tms_keycloak_bootstrap_user='bootstrap')
        for role, register, fields in (
                ('keycloak', 'keycloak_identity', ('admin_password', 'operator_password')),
                ('backend', 'backend_verification', ('password',))):
            task = next(t for t in self.config.tasks(role) if t.get('register') == register)
            payload = json.loads(self.config.render(task['ansible.builtin.command']['stdin'], **values))
            self.assertTrue(task['no_log'])
            for field in fields:
                self.assertEqual(payload[field], password)
