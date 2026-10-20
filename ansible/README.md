# Install TMS with Ansible

Install TMS on a **dedicated Debian 13 ARM64** machine using Ansible.
The installer sets up the application, MariaDB, Keycloak and HTTPS with NGINX.

**Requirements:** A fresh Debian 13 ARM64 target with SSH, Python 3 and a sudo-capable account; a Linux or WSL controller with Git, Python 3 and pip; SSH key access from controller to target. The standard installation requires **4 GiB RAM**. A [1 GB experimental profile](docs/operations.md#experimental-1-gb-arm64-profile) is also available.

> **Important:** Use a fresh machine. The installer will not adopt existing unmanaged MariaDB, Keycloak, NGINX or TMS installations, and it manages the entire NGINX configuration. Each deployment supports one target.

## 1. Prepare the controller

Clone the [TMS repository](https://github.com/amprnet-sweden/TMS) and enter its `ansible/` directory. Make sure your SSH key works with the target machine. Then run:

```bash
cp examples/inventory.yml inventory.yml
cp examples/deployment.json deployment.json
```

Edit **`inventory.yml`** with the target address and SSH account, and **`deployment.json`** with the public HTTPS origin. The hostname must resolve to your target from users' browsers. The HTTPS port must be reachable on the target and must **not be remapped through NAT**.

## 2. Install

```bash
export TMS_CONTROLLER_DIR="$HOME/.local/share/tms-native"
bash scripts/setup-controller.sh
bash install.sh inventory.yml deployment.json
```

If asked for a `BECOME password`, enter the target account's **sudo password**. Installation includes compiling the application on the target and can take a while, particularly on slower hardware. No Docker installation is required.

The installer reports major phases, elapsed time and a final success or failure summary. Long tasks print a brief waiting message once a minute. Use `bash install.sh --verbose inventory.yml deployment.json` for conventional Ansible output. See [installation logs and troubleshooting](docs/operations.md#watching-a-long-installation).

## 3. Trust the HTTPS certificate

The installer generates a private certificate authority for the configured hostname. Import the **public** certificate at `ansible/.local/tms-installation-ca.crt` into the browser or operating system trust store of each client that will access TMS. Do not distribute the private key.

Publicly trusted certificate issuance, HTTP redirects and firewall rules are **not** automatically configured. The installer does not automatically renew or replace certificates; plan these tasks separately.

## 4. Log in

Open **`<public-origin>/tms/`** in your browser.

On the controller, from `ansible/`, display the generated application account credentials:

```bash
"$TMS_CONTROLLER_DIR/venv/bin/python" scripts/show-keycloak-login.py appuser
```

For the Keycloak administration console, open **`<public-origin>/auth/admin/master/console/`** and use:

```bash
"$TMS_CONTROLLER_DIR/venv/bin/python" scripts/show-keycloak-login.py tms-admin
```

These accounts are distinct from the SSH account.

## 5. Keep installation credentials safe

Securely back up the controller's **`secrets/` and `tls/`** directories and retain the same `TMS_CONTROLLER_DIR`, inventory and deployment configuration. Never commit these directories. The vault password is stored alongside the encrypted vault, so backups of both must be protected as credentials.

You can rerun the installation command with unchanged settings and application artifacts. It preserves generated credentials and existing passwords. **This is not an application upgrade or backup/restore tool.** Changes to an installed backend artifact are rejected; plan backups, restoration and upgrades separately.

## Further information

- [Operations and advanced installation](docs/operations.md) — 1 GB profile, preflight, long builds, logs, repeat runs and limitations.
- [Developer notes](docs/development.md) — tests, playbook organization, generated artifacts and developer workflows.
- [Improvement backlog](docs/roadmap.md) — outstanding work and previously completed changes.
