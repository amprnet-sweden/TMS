"""Exercise hostname tasks against ordinary and cloud-init-managed hosts files."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from jinja2 import Template
import yaml


ROOT = Path(__file__).resolve().parents[1]
HOST = 'tms.example.test'
BLOCK = f'127.0.0.1 {HOST}'
MARKER = '# BEGIN TMS Ansible installation hostname'
TEMPLATE = '''## template:jinja
{# Preserve the cloud-init template and local hostname placeholders. #}
127.0.1.1 {{fqdn}} {{hostname}}
127.0.0.1 localhost
::1 localhost ip6-localhost ip6-loopback
'''


class HostnameTests(unittest.TestCase):
    def run_tasks(self, directory, hosts, cloud_template):
        tasks = yaml.safe_load((ROOT / 'roles/tls/tasks/hostname.yml').read_text())
        # Run the production modules on temporary files without root privileges.
        for task in tasks:
            for module in ('ansible.builtin.stat', 'ansible.builtin.blockinfile'):
                if module in task:
                    args = task[module]
                    args['path'] = str(hosts if args['path'] == '/etc/hosts' else cloud_template)
        play = directory / 'play.yml'
        play.write_text(yaml.safe_dump([{
            'hosts': 'localhost', 'gather_facts': False,
            'vars': {'tms_hostname': HOST, 'ansible_python_interpreter': sys.executable},
            'tasks': tasks,
        }]))
        executable = shutil.which('ansible-playbook') or str(Path(sys.executable).with_name('ansible-playbook'))
        env = {**os.environ, 'ANSIBLE_STDOUT_CALLBACK': 'default', 'ANSIBLE_NOCOLOR': '1',
               'ANSIBLE_LOCAL_TEMP': str(directory / 'local-tmp')}
        result = subprocess.run([executable, '-i', 'localhost,', '-c', 'local', str(play)],
                                capture_output=True, text=True, env=env, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_cloud_init_regeneration_preserves_mapping_and_convergence(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            hosts, cloud_template = directory / 'hosts', directory / 'hosts.debian.tmpl'
            hosts.write_text('127.0.0.1 localhost\n192.0.2.9 existing.example.test\n')
            cloud_template.write_text(TEMPLATE)
            self.run_tasks(directory, hosts, cloud_template)
            self.assertIn(BLOCK, hosts.read_text())
            self.assertIn('192.0.2.9 existing.example.test', hosts.read_text())
            self.assertTrue(cloud_template.read_text().startswith(TEMPLATE))
            before = (hosts.read_bytes(), cloud_template.read_bytes())
            self.assertRegex(self.run_tasks(directory, hosts, cloud_template), r'changed=0\s')
            self.assertEqual(before, (hosts.read_bytes(), cloud_template.read_bytes()))

            # Reproduce boot-time regeneration from the preserved Jinja template.
            rendered = Template(cloud_template.read_text()).render(hostname='pi', fqdn='pi.local')
            hosts.write_text(rendered + '\n')
            self.assertIn('127.0.1.1 pi.local pi', rendered)
            self.assertIn('::1 localhost ip6-localhost ip6-loopback', rendered)
            self.assertEqual(rendered.count(BLOCK), 1)
            self.assertEqual(rendered.count(MARKER), 1)
            self.assertRegex(self.run_tasks(directory, hosts, cloud_template), r'changed=0\s')

    def test_host_without_cloud_init_does_not_create_a_template(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            hosts, cloud_template = directory / 'hosts', directory / 'absent/hosts.debian.tmpl'
            hosts.write_text('127.0.0.1 localhost\n')
            self.run_tasks(directory, hosts, cloud_template)
            self.assertIn(BLOCK, hosts.read_text())
            self.assertFalse(cloud_template.exists())
            self.assertRegex(self.run_tasks(directory, hosts, cloud_template), r'changed=0\s')


if __name__ == '__main__':
    unittest.main()
