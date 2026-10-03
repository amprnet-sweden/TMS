# Native installation (preview)

Installs TMS on a dedicated **Debian 13 ARM64** host:
Java 21, Node 22, MariaDB 11.8, Keycloak 26.4.7, NGINX, frontend and backend.
Application builds run under an unprivileged account; services use separate
accounts. Databases and application listeners bind to loopback. NGINX provides
HTTPS, including WebSocket forwarding.
The standard profile requires 4 GiB RAM; an experimental 1 GB profile is
described below.

This is an initial-installation contribution for review. Component playbooks
passed repeated zero-change runs on an emulated ARM64 VM. Browser login,
incident persistence, live updates between windows and recovery after reboot
were verified on that VM. A clean installation using this consolidated entry
point passed on a physical 1 GB Raspberry Pi 3 using the experimental profile:
on-target builds, API/STOMP checks, a zero-change rerun and automatic recovery
after reboot. Browser login/logout, saves and live updates passed, including
saves and live updates after reboot. Capacity testing and backup restoration
are outside this contribution's validation scope.

## Install

Use a fresh target with SSH, Python 3 and a sudo account already configured.
The playbooks refuse to adopt existing unmanaged MariaDB, Keycloak, NGINX or
TMS installations. They manage the complete NGINX configuration and support
one target per deployment.

On a Linux controller or WSL, install Git and Python 3 with pip, clone this
repository, and enter `ansible/`. Configure SSH key authentication to the target.

```bash
cp examples/inventory.yml inventory.yml
cp examples/deployment.json deployment.json
# Edit both copies: target address/account and the public HTTPS origin.
export TMS_CONTROLLER_DIR="$HOME/.local/share/tms-native"
bash scripts/setup-controller.sh
bash install.sh inventory.yml deployment.json
```

`BECOME password` means the target account's sudo password. Builds can take
several minutes under emulation. The source snapshot includes tracked working
tree edits and the frontend lockfile; commit new application files before building.
Builds skip Docker-dependent backend tests. No Docker installation is required.

The configured DNS hostname must resolve to the target from browsers. The
HTTPS port must be reachable and identical externally and on the target; do
not remap it through NAT. The playbook maps that hostname to loopback inside
the target. HTTP redirect, public certificate issuance and firewall management
are outside this preview.

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

For hardware validation on a 1 GB Debian 13 ARM64 host, explicitly add
`"tms_resource_profile": "pi_1gb_experimental"` to deployment.json.
Omitting this setting selects `standard` and retains the 4 GB requirement.
The experimental profile requires at least 850 MiB usable RAM and uses trial
256 MiB heaps for each Java service, one Gradle worker, bounded build heaps,
and a smaller MariaDB buffer pool. JVM native memory is additional to heap.
Installation and functional checks passed on a physical 1 GB Pi 3 with
approximately 904 MiB of existing zram swap. This is an experimental profile;
the result does not establish sustained workload capacity.

The installer does not add or resize swap. On-target builds may be slow or
fail on this hardware. Measure memory pressure, service restarts and latency
during installation, concurrent browser use and reboot recovery before
relying on the profile. A separate build-host workflow is not implemented yet.

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
ignored by Git. Reports omit credentials. No application backup/restore or
upgrade workflow is provided yet; a changed installed backend artifact is
rejected rather than silently upgraded. Keep this preview on a disposable host
until those workflows and hardware acceptance are completed.

Checks cover artifact hashes, database account isolation, HTTPS validation,
Keycloak permissions and assets, migrations, authenticated API reads and STOMP
authentication. Browser writes and two-window live updates require acceptance
testing on the resulting deployment.

## Development checks

```bash
"$TMS_CONTROLLER_DIR/venv/bin/python" -m unittest discover -s tests -v
"$TMS_CONTROLLER_DIR/venv/bin/ansible-galaxy" collection install -r requirements.yml -p .local/collections
ANSIBLE_COLLECTIONS_PATH="$PWD/.local/collections" \
  "$TMS_CONTROLLER_DIR/venv/bin/ansible-playbook" -i examples/inventory.yml site.yml --syntax-check
```

Run the backend authentication regression tests separately with Java 21:
`./gradlew test --tests se.amprnet.tms.messaging.WebSocketAuthenticatorServiceTests`
from `backend/`. The installer pins its controller, Node and Keycloak versions;
review and update those pins deliberately.
