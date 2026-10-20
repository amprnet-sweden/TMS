"""Concise installer presentation; execution and failure diagnostics stay with Ansible."""
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import threading
import time

from ansible.plugins.callback.default import CallbackModule as DefaultCallback

DOCUMENTATION = """
name: tms_progress
type: stdout
short_description: Concise native installer phases and waiting status
description: Uses Ansible's standard failure diagnostics and secret masking.
extends_documentation_fragment:
  - default_callback
  - result_format_callback
"""

PHASES = {
    'preflight': 'Preflight', 'prerequisites': 'Prerequisites',
    'backend_build': 'Backend build', 'frontend_build': 'Frontend build',
    'database': 'Database', 'https': 'HTTPS', 'keycloak': 'Keycloak',
    'application': 'Application deployment', 'verification': 'Verification',
    'installation': 'Installation',
}
BUILD_LOGS = {
    'build_backend_status': 'build-status.log',
    'build_frontend_dependencies_status': 'dependencies-status.log',
    'build_frontend_status': 'build-status.log',
}
GRADLE_TASKS = frozenset('compileJava processResources classes resolveMainClassName bootJar jar '
                         'assemble check build compileTestJava processTestResources testClasses'.split())


def duration(seconds):
    minutes, seconds = divmod(max(0, int(seconds)), 60)
    return f'{minutes}m {seconds:02d}s' if minutes else f'{seconds}s'


def registration(task):
    value = task.register
    # ansible-core 2.21 converts simple register names into result projections.
    if isinstance(value, dict) and len(value) == 1:
        value = next(iter(value))
    return value if isinstance(value, str) else None


def phase_for(task):
    # Optional phase tags are useful for standalone/local presentation checks.
    for phase in PHASES:
        if 'tms_phase_' + phase in task.tags:
            return phase
    path = task.get_path().replace('\\', '/').rsplit(':', 1)[0]
    if '/roles/backend/tasks/verify.yml' in path or '/roles/backend/tasks/report.yml' in path:
        return 'verification'
    role = task._role.get_name().split('.')[-1] if task._role else None
    if role == 'build':
        component = task.get_vars().get('component')
        if isinstance(component, dict) and component.get('name') in ('backend', 'frontend'):
            return component['name'] + '_build'
        return None
    roles = {'build_tools': 'prerequisites', 'database': 'database', 'tls': 'https',
             'frontend_proxy': 'https', 'keycloak': 'keycloak', 'backend': 'application'}
    if role in roles:
        return roles[role]
    return {'preflight.yml': 'preflight', 'build.yml': 'prerequisites', 'database.yml': 'database',
            'https.yml': 'https', 'keycloak.yml': 'keycloak', 'backend.yml': 'application'}.get(Path(path).name)


def safe_milestone(line):
    if not isinstance(line, str) or len(line) > 256:
        return None
    match = re.fullmatch(r'\[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ \+[0-9.]+s\] (.+)', line)
    if not match:
        return None
    message = match[1]
    if message.startswith('Gradle task: ') and message[13:] in GRADLE_TASKS:
        return message
    patterns = (r'BUILD (?:SUCCESSFUL|FAILED) in [0-9hms .]+',
                r'added \d+ packages(?:, and audited \d+ packages)? in [0-9.ms]+',
                r'Vite modules transformed: \d+')
    if any(re.fullmatch(pattern, message) for pattern in patterns):
        return message
    if message in ('Vite: transforming...', 'Vite: rendering chunks...',
                   'Vite: computing gzip size...', 'Vite build completed'):
        return message
    return None


class CallbackModule(DefaultCallback):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'tms_progress'
    INTERVAL = 60

    def __init__(self):
        super().__init__()
        self._began = time.monotonic()
        self._phase = None
        self._phase_started = None
        self._phase_changed = False
        self._phase_error = False
        self._completed = set()
        self._stop = threading.Event()
        self._worker = None
        self._retried = False
        self._task_phase = None
        self._no_hosts = False
        self._installation = False
        self._origin = None

    def _emit(self, message, color=None):
        if not sys.stdout.isatty():
            message = datetime.now(timezone.utc).strftime('[%Y-%m-%dT%H:%M:%SZ] ') + message
        self._display.display(message, color=color)

    def _stop_task(self):
        self._stop.set()
        if self._worker:
            self._worker.join()
            self._worker = None

    def _end_phase(self):
        if self._phase is None:
            return
        label = PHASES[self._phase]
        elapsed = duration(time.monotonic() - self._phase_started)
        if self._phase_error:
            self._emit(f'! {label} ended with task errors — {elapsed}', 'yellow')
        else:
            unchanged = ' (unchanged)' if not self._phase_changed and self._phase not in ('preflight', 'verification') else ''
            self._emit(f'✓ {label} complete{unchanged} — {elapsed}', 'green')
        self._completed.add(self._phase)
        self._phase = None

    def v2_playbook_on_start(self, playbook):
        self._began = time.monotonic()
        self._installation = Path(playbook._file_name).name == 'site.yml'
        self._emit('TMS Native Installer' if self._installation else 'TMS playbook')
        if self._installation:
            try:
                values = json.loads((Path(playbook._file_name).parent / '.local/deployment-vars.json').read_text())
                origin = values.get('tms_public_origin', '') if isinstance(values, dict) else ''
                if isinstance(origin, str) and re.fullmatch(r'https://[a-zA-Z0-9.-]+(?::[0-9]{1,5})?', origin):
                    self._origin = origin
            except (OSError, ValueError):
                pass

    def v2_playbook_on_play_start(self, play):
        self._stop_task()
        self._end_phase()
        self._play = play

    def _context(self, task):
        action = task.action.split('.')[-1]
        if action == 'apt':
            return 'package installation'
        if action == 'unarchive':
            return 'archive extraction'
        if task.until and action in ('uri', 'wait_for', 'command'):
            return 'Keycloak readiness' if self._task_phase == 'keycloak' else 'service readiness'
        if registration(task) == 'build_frontend_dependencies_status':
            return 'frontend dependency installation'
        if action == 'command' and task.async_val and self._task_phase == 'keycloak':
            return 'authentication service build'
        return PHASES.get(self._task_phase or self._phase, 'installation task').lower()

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._stop_task()
        self._last_task_name = None
        self._task_phase = phase_for(task)
        phase = self._task_phase
        # Repeated standalone-stage preflights still execute; display them once.
        if phase and phase != self._phase and phase not in self._completed:
            self._end_phase()
            self._phase = phase
            self._phase_started = time.monotonic()
            self._phase_changed = self._phase_error = False
            self._emit(f'• {PHASES[phase]}')
        self._retried = False
        context = self._context(task)
        log = BUILD_LOGS.get(registration(task))
        started = time.monotonic()
        self._stop = threading.Event()

        def heartbeat():
            while not self._stop.wait(self.INTERVAL):
                elapsed = duration(time.monotonic() - started)
                hint = f' Recorded milestones: target {log}.' if log else ''
                self._emit(f'  Still waiting for {context} ({elapsed} elapsed).{hint}')

        self._worker = threading.Thread(target=heartbeat, daemon=True)
        self._worker.start()

    def v2_playbook_on_handler_task_start(self, task):
        self.v2_playbook_on_task_start(task, False)

    def v2_runner_on_ok(self, result):
        self._stop_task()
        self._phase_changed |= bool(result.result.get('changed', False))
        self._handle_warnings_and_exception(result)
        if registration(result.task) in BUILD_LOGS and not result.result.get('_ansible_no_log'):
            lines = result.result.get('stdout_lines', [])
            for line in lines[-40:] if isinstance(lines, list) else []:
                if message := safe_milestone(line):
                    self._emit('  ' + message)

    def v2_runner_on_skipped(self, result):
        self._stop_task()

    def v2_runner_retry(self, result):
        if not self._retried:
            if result.task.until and result.task.action.split('.')[-1] in ('uri', 'wait_for', 'command'):
                service = 'Keycloak' if self._task_phase == 'keycloak' else 'the service'
                self._emit(f'  Waiting for {service} to become ready; startup retries are normal.')
            else:
                self._emit('  Retrying ' + self._context(result.task) + '; next attempt pending.')
            self._retried = True

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._stop_task()
        self._phase_error = True
        self._emit('! Task failed during ' + PHASES.get(self._task_phase or self._phase, 'installation'), 'red')
        super().v2_runner_on_failed(result, ignore_errors)

    def v2_runner_on_unreachable(self, result):
        self._stop_task()
        self._phase_error = True
        self._emit('! Target unreachable during ' + PHASES.get(self._task_phase or self._phase, 'installation'), 'red')
        super().v2_runner_on_unreachable(result)

    def v2_playbook_on_no_hosts_matched(self):
        self._no_hosts = True
        self._emit('! No deployment hosts matched the inventory.', 'red')

    def v2_playbook_on_stats(self, stats):
        self._stop_task()
        self._end_phase()
        summaries = [stats.summarize(host) for host in stats.processed]
        failed = self._no_hosts or not summaries or any(s['failures'] or s['unreachable'] for s in summaries)
        handled = any(s['rescued'] or s['ignored'] for s in summaries)
        elapsed = duration(time.monotonic() - self._began)
        subject = 'Installation' if self._installation else 'Playbook'
        if failed:
            self._emit(f'FAILED: {subject} did not complete — {elapsed}. See the task error above.', 'red')
            self._emit('Investigate the reported task; use --verbose for conventional Ansible output.')
        elif handled:
            self._emit(f'{subject} completed with handled task errors — {elapsed}. Review the errors above.', 'yellow')
        else:
            changes = sum(s['changed'] for s in summaries)
            self._emit(f'SUCCESS: {subject} completed — {elapsed}; {changes} changed task(s).', 'green')
            if self._installation and self._origin:
                self._emit(f'TMS: {self._origin}/tms/')
                self._emit('Next: trust .local/tms-installation-ca.crt on your browsing computer, '
                           'then retrieve appuser credentials with scripts/show-keycloak-login.py.')
                self._emit('Complete browser acceptance checks; preserve the controller secrets/ and tls/ directories.')

    def v2_runner_on_async_poll(self, result):
        pass

    def v2_runner_on_async_ok(self, result):
        pass

    def v2_runner_on_async_failed(self, result):
        pass

    def v2_runner_item_on_ok(self, result):
        pass

    def v2_runner_item_on_skipped(self, result):
        pass

    def v2_playbook_on_include(self, included_file):
        pass
