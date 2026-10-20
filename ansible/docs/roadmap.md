# Improvement backlog

Planning notes retained from the original Ansible README; completed items are recorded for reference.

## Planned improvements

The following improvements are listed in approximate priority order. Preserve
existing ownership checks, credential preservation, checksum verification and
repeat-run behavior throughout these changes.

- [x] **Define the Java version once.** Introduce `tms_java_version` and derive
  the package name, Java home, version assertions and task descriptions from it.
  Pass the Java executable to backend verification and the expected version to
  source preparation. Check that the independently declared Gradle toolchain
  requirement agrees with the installer.
- [x] **Use shared paths consistently across roles.** Move shared paths into
  common variables and replace hardcoded copies of `tms_build_root`,
  `tms_database_socket` and `tms_database_state_directory`, including paths in
  artifact validation patterns.
- [x] **Replace numbered inspection results with named results.** Replace
  references such as `keycloak_paths.results[4]` with individually registered
  results or dictionaries keyed by meaningful names, especially in ownership
  and prerequisite checks.
- [x] **Split large roles into named phases.** Extract validation, installation,
  configuration, verification and reporting task files from the backend,
  Keycloak and frontend/proxy roles. Static imports preserve task order and
  handler boundaries; identity provisioning and HTTPS trust setup have their
  own phases within their existing roles.
- [x] **Separate TLS and Java trust setup from the frontend/proxy role.** Move
  certificate installation and backend Java trust-store setup into a dedicated
  role so service prerequisites are explicit.
- [x] **Run installer checks in CI.** Run the Python helper tests, playbook
  syntax checks for both resource profiles and shell syntax checks on pull
  requests, using the pinned controller dependencies.
- [x] **Extract common controller and vault utilities.** Share controller-path
  resolution, vault access, validation and error handling between Python
  helpers while retaining explicit credential-preservation rules. Separate
  general deployment-variable generation from certificate preparation so
  deployment settings no longer depend on `tls-vars.json`.
- [x] **Make the build report an explicit interface between stages.** Include
  frontend/backend fingerprints and a report schema version, and validate
  required fields when consuming the report. Stop deriving release identifiers
  by splitting artifact directory paths.
- [x] **Show progress during long installation tasks.** Ensure status output
  appears promptly when piped to logs, add timestamps and elapsed time, and
  provide periodic status during builds, package installation and service
  readiness waits. Distinguish a running job from evidence of actual progress;
  expose bounded, credential-free build-log excerpts where useful. Preserve
  timeouts, failure exit codes and unchanged-run behavior. Document what users
  should expect and how to inspect a long-running task safely.
- [x] **Run preflight once during a complete installation.** Extract reusable
  stage plays so `site.yml` performs preflight once while standalone stage
  entry points retain their checks.
- [ ] **Support existing HTTPS certificates.** Allow operators to supply a
  certificate chain and private key instead of generating a private CA and
  server certificate. Validate the certificate and hostname, configure NGINX
  and backend Java trust appropriately, and document certificate renewal and
  reload responsibilities.
- [ ] **Provide a reusable installation and convergence test runner.** Accept
  inventory and deployment settings, run installation and an unchanged rerun,
  compare service process/start/restart state and perform authenticated checks.
  Preserve timestamped logs, exit codes and the exact tested source manifest.
  Keep credentials and personal lab paths outside the repository; distinguish
  fresh-install validation from checks against an existing managed host.
- [ ] **Define Java trust-store refresh behavior.** Incorporate system CA
  updates into the backend-specific trust store while preserving and verifying
  the installation CA. Define when a backend restart is required and verify
  that unchanged runs do not rebuild the store or restart services.
