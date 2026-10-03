#!/usr/bin/env python3
"""Add Keycloak credentials atomically; preserve all existing database credentials."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

FIELDS = ("tms_keycloak_bootstrap_password", "tms_keycloak_admin_password",
          "tms_keycloak_lookup_password", "tms_keycloak_operator_password")


def main():
    os.umask(0o077)
    controller = Path(os.environ.get("TMS_CONTROLLER_DIR", Path.home() / ".local/share/tms-ansible"))
    directory = controller / "secrets"
    key, vault = directory / "vault.key", directory / "vault.yml"
    if directory.is_symlink() or any(p.is_symlink() or not p.is_file() for p in (key, vault)):
        raise SystemExit("Run the database stage first; the original private vault/key pair is required.")
    tool = controller / "venv/bin/ansible-vault"
    values = json.loads(subprocess.run(
        [str(tool), "view", "--vault-password-file", str(key), str(vault)],
        capture_output=True, check=True).stdout)
    if not all(values.get(k) for k in ("tms_database_deployment_id", "tms_database_password", "tms_keycloak_database_password")):
        raise SystemExit("The original database credentials are required.")
    if all(values.get(k) for k in FIELDS):
        print("Reusing encrypted Keycloak credentials; no passwords changed.")
        return
    if any(k in values for k in FIELDS):
        raise SystemExit("Incomplete Keycloak credentials; restore the original vault rather than regenerating passwords.")
    pending = directory / "keycloak-vault.new"
    if pending.exists() or pending.is_symlink():
        raise SystemExit("An unfinished vault update exists; inspect the private secrets directory.")
    values.update({k: secrets.token_urlsafe(36) for k in FIELDS})
    subprocess.run([str(tool), "encrypt", "--vault-password-file", str(key), "--output", str(pending), "-"],
                   input=json.dumps(values).encode(), capture_output=True, check=True)
    pending.chmod(0o600)
    pending.replace(vault)
    print("Added encrypted Keycloak credentials; existing database credentials preserved.")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, ValueError):
        sys.exit("Vault update failed; check the original private vault/key pair locally.")
