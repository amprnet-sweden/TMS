import json
from pathlib import Path
import sys
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from deployment import load


class DeploymentTests(unittest.TestCase):
    def configuration(self, origin):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'deployment.json'
            path.write_text(json.dumps({'tms_public_origin': origin}))
            return load(path)

    def test_hostname_and_ports_reach_proxy_configuration(self):
        environment = Environment(undefined=StrictUndefined)
        environment.filters['urlsplit'] = lambda value, field: getattr(urlsplit(value), field)
        template = environment.from_string((ROOT / 'roles/frontend_proxy/templates/nginx.conf.j2').read_text())
        for origin, port in (('https://service.example.test', 443), ('https://other.example.test:9443', 9443)):
            values = self.configuration(origin)
            rendered = template.render(**values)
            self.assertIn(f'listen {port} ssl;', rendered)
            self.assertIn(f'server_name {urlsplit(origin).hostname};', rendered)
            self.assertIn(f'proxy_set_header Host {urlsplit(origin).netloc};', rendered)

    def test_invalid_or_noncanonical_origins_fail_before_provisioning(self):
        for origin in ('http://tms.example.test', 'https://tms.example.test/',
                       'https://user:secret@tms.example.test', 'https://tms.example.test:443',
                       'https://tms.example.test:0', 'https://tms.example.test;evil',
                       'https://tms.example.test?x=1', 'https://tms.example.test/#fragment'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                self.configuration(origin)
