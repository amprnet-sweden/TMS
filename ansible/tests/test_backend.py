"""Exercise deployment configuration and API verification failure detection."""
import importlib.util
import io
import json
from pathlib import Path
import unittest
from urllib.error import HTTPError
from urllib.parse import urlsplit

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('backend_verifier', ROOT / 'roles/backend/files/verify-backend.py')
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class FakeAPI:
    def __init__(self):
        self.calls = []
        self.allow_anonymous = False
        self.responses = {
            '/api/user': {'id': 'test-user-id', 'username': 'appuser', 'roles': ['tms-superuser']},
            '/api/missions': {'status': True, 'data': []},
            '/api/user/missions': {'status': True, 'data': []},
            '/api/keycloak/admin/users': [{'username': 'appuser'}],
            '/api/keycloak/admin/groups': [{'name': 'TMS Superusers'}],
            '/api/keycloak/admin/roles': [{'name': 'tms-superuser'}],
            '/auth/realms/amprnet/protocol/openid-connect/token': {'access_token': 'test-token'},
        }

    def open(self, request, timeout):
        path = urlsplit(request.full_url).path
        self.calls.append((request.get_method(), path))
        authenticated = (request.get_header('Authorization') == 'Bearer test-token'
                         or request.get_header('Cookie') == 'JWT=test-token')
        if path == '/api/user' and not authenticated and not self.allow_anonymous:
            raise HTTPError(request.full_url, 401, 'Unauthorized', {}, None)
        return io.BytesIO(json.dumps(self.responses[path]).encode())


class BackendTests(unittest.TestCase):
    def test_success_checks_cookie_bearer_database_and_lookups_without_writes(self):
        api = FakeAPI()
        result = verifier.verify('https://example.test', 'test-password', api)
        self.assertEqual(result['java_https_jwt_and_lookup'], 'passed')
        self.assertEqual(result['browser_workflows'], 'pending')
        self.assertEqual([path for method, path in api.calls if method != 'GET'],
                         ['/auth/realms/amprnet/protocol/openid-connect/token'])
        self.assertNotIn('test-token', json.dumps(result))
        self.assertNotIn('test-password', json.dumps(result))

    def test_rejects_unprotected_api(self):
        api = FakeAPI()
        api.allow_anonymous = True
        with self.assertRaisesRegex(RuntimeError, 'unexpectedly accepted'):
            verifier.verify('https://example.test', 'test-password', api)

    def test_rejects_failed_database_or_missing_identity_results(self):
        for path, response in (
                ('/api/user', {'id': 'test-user-id', 'username': 'appuser', 'roles': []}),
                ('/api/missions', {'status': False, 'data': []}),
                ('/api/keycloak/admin/users', []),
                ('/api/keycloak/admin/groups', []),
                ('/api/keycloak/admin/roles', [])):
            with self.subTest(path=path):
                api = FakeAPI()
                api.responses[path] = response
                with self.assertRaises(RuntimeError):
                    verifier.verify('https://example.test', 'test-password', api)

    def test_native_configuration_resolves_urls_and_keeps_secrets_out_of_yaml(self):
        template = (ROOT / 'roles/backend/templates/application.yaml.j2').read_text()
        rendered = Environment(undefined=StrictUndefined).from_string(template).render(
            tms_public_origin='https://tms.example.test:8443', tms_tenant='default')
        config = yaml.safe_load(rendered)
        self.assertEqual(config['server']['address'], '127.0.0.1')
        self.assertFalse(config['tms']['demo'])
        self.assertEqual(config['keycloak']['uri'], 'https://tms.example.test:8443/auth')
        self.assertEqual(config['keycloak']['password'], '${TMS_KEYCLOAK_LOOKUP_PASSWORD}')
        self.assertEqual(config['spring']['datasource']['password'], '${TMS_DATABASE_PASSWORD}')
        jwt = config['spring']['security']['oauth2']['resourceserver']['jwt']
        self.assertEqual(jwt['jwk-set-uri'], jwt['issuer-uri'] + '/protocol/openid-connect/certs')


if __name__ == '__main__':
    unittest.main()
