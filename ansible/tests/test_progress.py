"""Progress must be prompt, bounded, private and preserve failed build status."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'roles/build_tools/files/build-status.py'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProgressTests(unittest.TestCase):
    def test_extracted_stage_paths_keep_their_progress_phase(self):
        module = load('stage_progress_callback', ROOT / 'callback_plugins/tms_progress.py')
        for stage, phase in (('build', 'prerequisites'), ('database', 'database'), ('https', 'https'),
                             ('keycloak', 'keycloak'), ('backend', 'application')):
            with self.subTest(stage=stage):
                task = SimpleNamespace(tags=[], _role=None, get_path=lambda: f'/installer/{stage}-stage.yml:4')
                self.assertEqual(module.phase_for(task), phase)

    def playbook(self, tasks, *, callback='tms_progress', connection='local', variables=None, role_files=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugins = root / 'callback_plugins'
            plugins.mkdir()
            for name, content in (role_files or {}).items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            source = (ROOT / 'callback_plugins/tms_progress.py').read_text()
            (plugins / 'tms_progress.py').write_text(source.replace('INTERVAL = 60', 'INTERVAL = 0.2'))
            (root / '.local').mkdir()
            (root / '.local/deployment-vars.json').write_text(json.dumps({'tms_public_origin': 'https://service.example.test:9443'}))
            play = root / 'site.yml'
            values = {'ansible_python_interpreter': sys.executable, 'ansible_async_dir': str(root / 'async')}
            values.update(variables or {})
            play.write_text(json.dumps([{'hosts': 'localhost', 'connection': connection, 'gather_facts': False,
                                        'vars': values, 'tasks': tasks(root) if callable(tasks) else tasks}]))
            env = dict(os.environ, PYTHONUNBUFFERED='1', ANSIBLE_CALLBACK_PLUGINS=str(plugins),
                       ANSIBLE_STDOUT_CALLBACK=callback, ANSIBLE_NOCOLOR='1',
                       ANSIBLE_LOCAL_TEMP=str(root / 'local'),
                       ANSIBLE_REMOTE_TEMP=str(root / 'remote'))
            env.pop('ANSIBLE_CALLBACKS_ENABLED', None)
            binary = Path(sys.executable).parent / 'ansible-playbook'
            process = subprocess.Popen([str(binary), '-i', 'localhost,', str(play),
                                        '-e', json.dumps({'ansible_python_interpreter': sys.executable})], env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output = []
            live = False
            deadline = threading.Timer(30, process.kill)
            deadline.start()
            try:
                for line in process.stdout:
                    output.append(line)
                    if 'Still waiting for' in line and process.poll() is None:
                        live = True
                process.wait(timeout=30)
            finally:
                deadline.cancel()
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
            output = ''.join(output)
            self.assertNotIn('Callback dispatch', output)
            return process.returncode, output, live

    def test_normal_execution_has_phases_url_and_no_internal_noise(self):
        phases = ('preflight', 'prerequisites', 'backend_build', 'frontend_build',
                  'database', 'https', 'keycloak', 'application', 'verification')
        tasks = [{'name': 'Internal assertion with private-sentinel', 'ansible.builtin.debug': {'msg': 'private-sentinel'},
                  'tags': ['tms_phase_' + phase], 'no_log': True} for phase in phases]
        code, output, _ = self.playbook(tasks)
        self.assertEqual(code, 0, output)
        for label in ('Preflight', 'Prerequisites', 'Backend build', 'Frontend build', 'Database', 'HTTPS',
                      'Keycloak', 'Application deployment', 'Verification'):
            self.assertIn(label + ' complete', output)
        self.assertIn('SUCCESS: Installation completed', output)
        self.assertIn('https://service.example.test:9443/tms/', output)
        self.assertIn('Next: trust', output)
        for noise in ('private-sentinel', 'TASK [', 'PLAY RECAP', 'Task boundary', 'ok: ['):
            self.assertNotIn(noise, output)

    def test_long_async_operation_has_live_heartbeat_without_duplicate_polling(self):
        code, output, live = self.playbook([{'name': 'Long operation', 'ansible.builtin.command': '/bin/sleep 1',
                                            'async': 10, 'poll': 1, 'changed_when': False,
                                            'tags': ['tms_phase_prerequisites']}])
        self.assertEqual(code, 0, output)
        self.assertTrue(live, output)
        self.assertIn('Still waiting for prerequisites', output)
        for noise in ('ASYNC POLL', 'ASYNC OK', 'no forward progress', 'build-status.log'):
            self.assertNotIn(noise, output)
        callback = load('progress_callback', ROOT / 'callback_plugins/tms_progress.py')
        self.assertEqual(callback.CallbackModule.INTERVAL, 60)

    def test_dynamic_component_phases_include_reused_builds_without_playbook_changes(self):
        files = {'roles/build/tasks/main.yml': '''
- ansible.builtin.include_tasks: component.yml
  loop:
    - name: backend
    - name: frontend
  loop_control:
    loop_var: component
''', 'roles/build/tasks/component.yml': '''
- name: Inspect completion marker
  ansible.builtin.debug:
    msg: Existing marker and artifact
- name: Build only when needed
  ansible.builtin.command: /bin/false
  when: false
'''}
        code, output, _ = self.playbook([{'ansible.builtin.include_role': {'name': 'build'}}], role_files=files)
        self.assertEqual(code, 0, output)
        self.assertIn('Backend build complete (unchanged)', output)
        self.assertIn('Frontend build complete (unchanged)', output)
        self.assertLess(output.index('Backend build complete'), output.index('Frontend build complete'))
        self.assertIn('0 changed task(s)', output)

    def test_readiness_retries_are_explained_once_and_then_succeed(self):
        def tasks(root):
            counter = root / 'attempts'
            script = ('from pathlib import Path; import sys; p=Path(' + repr(str(counter)) + '); '
                      'n=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(n)); sys.exit(0 if n>=3 else 1)')
            return [{'name': 'Wait for service', 'ansible.builtin.command': {'argv': [sys.executable, '-c', script]},
                     'register': 'ready', 'until': 'ready.rc == 0', 'retries': 4, 'delay': 0,
                     'changed_when': False, 'tags': ['tms_phase_keycloak']}]
        code, output, _ = self.playbook(tasks)
        self.assertEqual(code, 0, output)
        self.assertEqual(output.count('startup retries are normal'), 1, output)
        self.assertNotIn('FAILED - RETRYING', output)
        self.assertNotIn('build-status.log', output)
        self.assertIn('SUCCESS:', output)

    def test_actual_failure_retains_error_exit_code_and_stage(self):
        code, output, _ = self.playbook([{'name': 'Build failure', 'ansible.builtin.command':
            {'argv': [sys.executable, '-c', 'import sys; print("actual build error"); sys.exit(23)']},
            'tags': ['tms_phase_backend_build']}])
        self.assertEqual(code, 2, output)
        self.assertIn('actual build error', output)
        self.assertIn('"rc": 23', output)
        self.assertIn('Task failed during Backend build', output)
        self.assertIn('FAILED: Installation', output)
        self.assertNotIn('SUCCESS:', output)
        self.assertNotIn('Backend build complete', output)

    def test_timeout_still_fails_and_no_log_masks_private_details(self):
        code, output, _ = self.playbook([{'name': 'Private timeout', 'ansible.builtin.command':
            {'argv': [sys.executable, '-c', 'import time; print("private-sentinel", flush=True); time.sleep(10)']},
            'async': 1, 'poll': 1, 'no_log': True, 'tags': ['tms_phase_backend_build']}])
        self.assertEqual(code, 2, output)
        self.assertNotIn('private-sentinel', output)
        self.assertIn('FAILED: Installation', output)
        self.assertIn('censored', output)

    def test_rescued_failure_is_not_presented_as_clean_success(self):
        code, output, _ = self.playbook([{'block': [{'name': 'Expected failed check',
            'ansible.builtin.fail': {'msg': 'expected failure'}}], 'rescue': [
            {'ansible.builtin.debug': {'msg': 'recovered'}}], 'tags': ['tms_phase_verification']}])
        self.assertEqual(code, 0, output)
        self.assertIn('completed with handled task errors', output)
        self.assertNotIn('SUCCESS:', output)

    def test_unreachable_target_is_not_presented_as_success(self):
        code, output, _ = self.playbook([{'ansible.builtin.command': '/bin/true', 'tags': ['tms_phase_preflight']}],
            connection='ssh', variables={'ansible_host': '127.0.0.1', 'ansible_port': 1,
                                         'ansible_ssh_timeout': 1, 'ansible_ssh_common_args': '-o BatchMode=yes'})
        self.assertNotEqual(code, 0, output)
        self.assertIn('UNREACHABLE', output)
        self.assertIn('FAILED: Installation', output)
        self.assertNotIn('SUCCESS:', output)

    def test_milestones_are_allowlisted_and_full_details_remain_in_verbose_mode(self):
        line = '[2026-10-20T06:25:32Z +17.0s] Gradle task: bootJar'
        tasks = [{'name': 'Internal build', 'ansible.builtin.command': {'argv': [sys.executable, '-c',
                  'print(' + repr(line) + '); print("private-sentinel")']},
                  'register': 'build_backend_status', 'tags': ['tms_phase_backend_build']}]
        code, output, _ = self.playbook(tasks)
        self.assertEqual(code, 0, output)
        self.assertIn('Gradle task: bootJar', output)
        self.assertNotIn('private-sentinel', output)
        code, output, _ = self.playbook(tasks, callback='default')
        self.assertEqual(code, 0, output)
        self.assertIn('TASK [Internal build]', output)
        self.assertIn('PLAY RECAP', output)

    def test_live_log_is_bounded_private_and_filters_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'build-status.log'
            code = '''
import time
print('secret=https://user:password@example.test', flush=True)
print('> Task :compileJava', flush=True)
time.sleep(1)
for _ in range(60): print('> Task :build')
print('> Task :build password=secret')
print('> Task :secret')
print('x' * 100000)
raise SystemExit(23)
'''
            process = subprocess.Popen([sys.executable, str(HELPER), str(log),
                                        sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    if log.exists() and 'compileJava' in log.read_text():
                        break
                    time.sleep(.02)
                self.assertIsNone(process.poll(), 'Milestone must be visible before completion')
                self.assertIn('compileJava', log.read_text())
                stdout, stderr = process.communicate(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
            self.assertEqual(process.returncode, 23, stderr)
            self.assertEqual(len(log.read_text().splitlines()), 40)
            self.assertIn(b'Build exited with status 23', stdout)
            self.assertNotIn(b'secret', stdout + stderr + log.read_bytes())
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)

    def test_signal_exit_and_missing_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'status'
            for argv, expected in ((['/does/not/exist'], 127),
                                   ([sys.executable, '-c', 'import os, signal; os.kill(os.getpid(), signal.SIGTERM)'], 143)):
                result = subprocess.run([sys.executable, str(HELPER), str(log), *argv], capture_output=True)
                self.assertEqual(result.returncode, expected)

    def test_malformed_milestones_cannot_inject_arbitrary_output(self):
        module = load('milestones_callback', ROOT / 'callback_plugins/tms_progress.py')
        for line in ('password=secret', '[2026-10-20T06:25:32Z +17s] Gradle task: secret',
                     '[2026-10-20T06:25:32Z +17s] Gradle task: bootJar\npassword=secret', None):
            self.assertIsNone(module.safe_milestone(line))


if __name__ == '__main__':
    unittest.main()
