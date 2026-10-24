# Operations and advanced installation

This document contains detailed operational guidance for the Ansible-based TMS installer. Start with [the installation README](../README.md).

## Deployment and validation scope

The native stack uses Java 25, Node 22, MariaDB 11.8, Keycloak 26.8.1 and NGINX.
Application builds run under an unprivileged account; services use separate
accounts. Databases and application listeners bind to loopback. NGINX provides
HTTPS, including WebSocket forwarding.

Installation and functional checks passed on an emulated ARM64 VM and a physical
1 GB Raspberry Pi 3 using the experimental profile. Historical Pi validation
covered on-target builds, API/STOMP checks, unchanged reruns, browser login/logout,
incident saves, live updates and recovery after reboot. Those physical-Pi results
predate the progress-reporting changes. The progress work received fresh standard
profile VM installation/convergence checks; the subsequent presentation revision
was tested with local playbooks and demonstrations. Sustained workload capacity
and backup restoration have not been validated.

## Installation notes and network requirements

`BECOME password` means the target account's sudo password. Builds can take
several minutes under emulation. The source snapshot includes tracked working
tree edits and the frontend lockfile; commit new application files before building.
Builds skip Docker-dependent backend tests. No Docker installation is required.

The configured DNS hostname must resolve to the target from browsers. The
HTTPS port must be reachable and identical externally and on the target; do
not remap it through NAT. The playbook maps that hostname to loopback inside
the target. If the Debian cloud-init hosts template is present, the installer
also adds that mapping to the template so it survives hosts-file regeneration
at reboot. Configure HTTP redirect, public certificate issuance and firewall
rules separately if required; the installer does not manage them.

The installer creates a private CA restricted to that hostname. Import the
public `.local/tms-installation-ca.crt` into your browser/OS trust store.
The CA private key stays on the controller. Certificate replacement and renewal
are deliberate operations; expired or mismatched certificates cause a failure.

Open `<public-origin>/tms/`. Retrieve the generated application login locally:

```bash
"$TMS_CONTROLLER_DIR/venv/bin/python" scripts/show-keycloak-login.py appuser
```

Use `tms-admin` instead for `<public-origin>/auth/admin/master/console/`.
These are application accounts, separate from the SSH account. The temporary
bootstrap administrator is removed after permanent administrator verification.

## Experimental 1 GB ARM64 profile

To install on a 1 GB Debian 13 ARM64 host, explicitly add
`"tms_resource_profile": "pi_1gb_experimental"` to deployment.json.
Omitting this setting selects `standard` and retains the 4 GB requirement.
The experimental profile requires at least 850 MiB usable RAM and uses
256 MiB heaps for each Java service, one Gradle worker, bounded build heaps,
and a smaller MariaDB buffer pool. JVM native memory is additional to heap.
Installation and functional checks passed on a physical 1 GB Pi 3 with
approximately 904 MiB of existing zram swap. This is an experimental profile;
the result does not establish sustained workload capacity.

The installer does not add or resize swap. On-target builds may be slow or
fail on this hardware. Measure memory pressure, service restarts and latency
during installation, concurrent browser use and reboot recovery before
relying on the profile. Application builds run on the target; the installer
does not support a separate build host.

Read-only eligibility and sudo verification can be run before installation:

```bash
"$TMS_CONTROLLER_DIR/venv/bin/ansible-playbook" -i inventory.yml preflight.yml \
  -e tms_resource_profile=pi_1gb_experimental --ask-become-pass
```

## Repeat and preserve

Repeat the same install command to verify convergence. Keep the same
`TMS_CONTROLLER_DIR`, inventory and deployment settings. Credentials are generated
once and reused; existing passwords are not reset. Preserve the controller's
`secrets/` and `tls/` directories securely for recovery. The vault password is
stored alongside the encrypted vault with private filesystem permissions;
protect backups of both as credentials. Never commit these directories.

`.local/` contains generated archives, public CA, variables and reports and is
ignored by Git. Reports omit credentials. The installer handles initial
installation and repeat runs with the same application artifacts. It does not
provide application backup/restore or upgrades; a changed installed backend
artifact is rejected. Plan application backups, restoration and upgrades
separately when operating a deployment.

Checks cover artifact hashes, database account isolation, HTTPS validation,
Keycloak permissions and assets, migrations, authenticated API reads and STOMP
authentication. Browser writes and two-window live updates are manual checks
and are not part of the automated installer checks.

## Watching a long installation

The default output shows installation phases and their elapsed time. Long tasks
print a contextual waiting message once a minute. Waiting means the task has not
returned; it does not establish forward progress. Normal service readiness retries
are explained once. Use the final success/failure summary and installer exit code
to judge completion. Redirected output remains unbuffered and includes UTC timestamps.

For conventional Ansible task output and the PLAY RECAP, use:

```bash
bash install.sh --verbose inventory.yml deployment.json
```

To keep a log and preserve the installer failure status, use Bash pipefail:

```bash
set -o pipefail
bash install.sh inventory.yml deployment.json 2>&1 | tee installation.log
```

Application builds retain the one-hour async deadline and 15-second polling;
Keycloak retains its 30-minute deadline. Package and readiness timeouts are
unchanged. Status reporting does not start extra remote jobs or restart services.
Unchanged application artifacts still skip their builds, including log writes.

Gradle/npm builds write private, bounded status files on the target, under
`<tms_build_root>/backend/<backend_fingerprint>/backend/build-status.log` and
`<tms_build_root>/frontend/<frontend_fingerprint>/frontend/build-status.log`.
The npm dependency step uses `dependencies-status.log` in that frontend directory.
The default build root is `/var/lib/tms-build`; fingerprinted directory paths appear
in verbose output and the build report. Each file contains at most 40 timestamped entries;
recognized Gradle tasks, npm dependency counts and Vite phases are evidence of
tool activity, not a percentage complete. Quiet downloads, compilation and
Keycloak optimization can still have no recognized milestones. Compact output
shows recognized milestones after each build command completes; Ansible's async
polls do not stream partial build output. Failed builds retain their original
exit status and bounded excerpt in Ansible's failure result.

For safe inspection during a build, connect using your configured target SSH
account and run, replacing the path with that build's exact path:

```bash
sudo tail -n 40 '/var/lib/tms-build/backend/<backend_fingerprint>/backend/build-status.log'
```

Replace the angle-bracket placeholder before running the command.
These files contain only recognized milestones and fixed status messages;
arbitrary compiler/npm output is discarded because it can include credentials.
Failure diagnosis may therefore require deliberately reproducing the failed
command on the target as the build account and examining its output locally.
Avoid publishing raw build output, service journals, environment files, vault
contents or Ansible async result files. A missing/unchanged milestone file alone
does not establish a hang. For standalone playbooks, enable the same reporting
with `PYTHONUNBUFFERED=1 ANSIBLE_CALLBACK_PLUGINS="$PWD/callback_plugins"
ANSIBLE_STDOUT_CALLBACK=tms_progress` before `ansible-playbook`.
