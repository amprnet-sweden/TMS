# Developer notes

Developer-facing instructions and implementation details moved from the Ansible README.

## Development checks

The `Native installer checks` GitHub Actions workflow runs these checks on every
pull request and push to `main`, using `scripts/setup-controller.sh` for the same
pinned controller dependencies as local development. It checks both resource
profiles without connecting to a deployment host.

```bash
"$TMS_CONTROLLER_DIR/venv/bin/python" -m unittest discover -s tests -v
"$TMS_CONTROLLER_DIR/venv/bin/ansible-galaxy" collection install -r requirements.yml -p .local/collections
for profile in standard pi_1gb_experimental; do
  ANSIBLE_COLLECTIONS_PATH="$PWD/.local/collections" \
    "$TMS_CONTROLLER_DIR/venv/bin/ansible-playbook" -i examples/inventory.yml \
      site.yml --syntax-check -e "tms_resource_profile=$profile" || exit
done
bash -n install.sh scripts/setup-controller.sh
```

Run the backend authentication regression tests separately with Java 25:
`./gradlew test --tests se.amprnet.tms.messaging.WebSocketAuthenticatorServiceTests`
from `backend/`. The installer pins its controller, Node and Keycloak versions;
review and update those pins deliberately.

The backend, Keycloak and frontend/proxy roles use ordered static task imports
from `tasks/main.yml`. Read these entry points to follow each role through its
validation, installation, configuration, verification and reporting phases.
Keycloak identity provisioning remains an explicit phase. In `https.yml`, the
`tls` role runs before `frontend_proxy`: it checks HTTPS ownership and the CA pin,
installs certificates, maps the canonical hostname and prepares the backend Java
trust store. Java must already be installed by the build stage. Certificate changes
notify the proxy role's NGINX handlers, which run after proxy configuration and
before HTTPS verification.

Shared target paths are defined in `vars/common.yml`. The Java version is defined
in `vars/build.yml`; source preparation checks that `backend/build.gradle`
selects the same compiler. Update both declarations together when upgrading Java.

Controller helpers share path resolution, vault I/O, file validation and safe
error reporting in `scripts/controller.py`. Only `prepare-database-vault.py`
initializes credentials; `prepare-keycloak-vault.py` adds missing Keycloak fields
to a complete database vault. Existing credentials and unchanged ciphertext are
preserved, and incomplete credentials or unfinished updates require deliberate
recovery. `show-keycloak-login.py` uses the same validated vault access.

`install.sh` first runs `prepare-deployment.py DEPLOYMENT.json` to generate
`.local/deployment-vars.json` independently of certificates or vault state.
`prepare-tls.py` reads the same deployment settings and writes only certificate
paths, fingerprints and expiry to `.local/tls-vars.json`. The installer passes
both files explicitly. For manual stage invocations, pass
`--extra-vars @.local/deployment-vars.json` alongside the source, TLS and vault
inputs that stage requires; general deployment settings are no longer bundled
into `tls-vars.json`.

The build stage writes `{{ tms_build_root }}/build-report.json` as the interface
to frontend and backend deployment. Schema version 1 includes explicit
`backend_fingerprint` and `frontend_fingerprint` values, source/recipe provenance,
artifact locations, the backend SHA-256 and the frontend file checksum manifest.
Both consumers validate the version, required fields, canonical origin and
fingerprinted artifact paths before checking the actual artifact checksums.
Frontend release identifiers come from `frontend_fingerprint`; backend releases
remain identified by the JAR checksum. Additional informational fields are allowed.
Unversioned or unsupported reports are rejected; rerun the build stage with the
same installer to regenerate them. Existing ownership and upgrade guards still
apply. Changes to the build role also change the recipe fingerprint and may
rebuild artifacts, so use a fresh target for validating this change rather than
bypassing the backend upgrade guard on an existing deployment.

## Installer output

`install.sh` selects the `tms_progress` stdout callback by default. `--verbose`
selects Ansible's standard stdout callback instead; both modes keep Python output
unbuffered. Neither mode changes execution, async deadlines, polling intervals,
readiness retries, failure return codes or the artifact-reuse checks. No automatic
diagnostic log is created. Operators can capture verbose output in a private log.

The compact callback groups tasks into preflight, prerequisites, backend build,
frontend build, database, HTTPS, Keycloak, application deployment and verification.
It uses existing role names, task-file paths and the known component include
variable (`backend`/`frontend`); it does not template or print arbitrary task variables.
Repeated stage preflights still execute but are presented once. Unchanged phases
are labelled accordingly. Phase timing covers Ansible execution, not controller
preparation or password entry before the playbook starts.

Each pending task has a controller-side waiting timer of 60 seconds. Package and
archive operations get specific wording; only the three application build commands
get a status-file hint. Async poll messages and routine successful/skipped results
are suppressed. A readiness task's first retry explains the normal startup wait.
The callback never treats a waiting timer as proof of remote progress. Piped output
uses ordinary timestamped lines and no cursor movement.

Failures and unreachable hosts use Ansible's standard error renderer, including
`no_log` masking and source locations. Ignored/rescued errors are not presented as
a clean success. Successful full installations finish with the validated TMS URL
and next steps; standalone stage playbooks report only playbook completion.

The existing remote build helper retains at most 40 safe milestone entries and
discards arbitrary compiler/package output. The compact callback revalidates the
recognized entries before displaying them, without dumping command results or
debug variables. These excerpts become available when a build command completes.
Live Gradle/npm/Vite streaming is not provided: standard async callback events
do not include partial stdout, and callbacks have no authenticated channel for
reading private target files. Adding such a channel would be a separate execution
or action-plugin change, with additional timeout, permission and secrecy testing.

`tests/test_progress.py` exercises real local playbooks with an accelerated test
timer: phase grouping and reuse, piped waiting output, retries, actual command
errors, async deadlines, secret masking, unreachable targets, rescued failures,
milestone validation and standard verbose output. Controller workflow tests also
check `install.sh --verbose` and credential preservation in both output modes.
