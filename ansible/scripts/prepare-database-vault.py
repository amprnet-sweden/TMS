#!/usr/bin/env python3
"""Create a private deployment vault once; never print or silently replace credentials."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import uuid


def main():
    os.umask(0o077)
    controller = Path(os.environ.get("TMS_CONTROLLER_DIR", Path.home() / ".local/share/tms-ansible"))
    directory = controller / "secrets"
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink():
        raise SystemExit("Refusing to use a symlink for the secrets directory.")
    directory.chmod(0o700)
    key = directory / "vault.key"
    vault = directory / "vault.yml"
    tool = controller / "venv/bin/ansible-vault"
    for path in (key, vault):
        if path.is_symlink():
            raise SystemExit("Refusing to use symlinked vault files.")
    if key.exists() != vault.exists():
        raise SystemExit("Incomplete vault/key pair. Restore the original pair; credentials will not be regenerated.")
    if key.exists():
        key.chmod(0o600)
        vault.chmod(0o600)
        decrypted = subprocess.run(
            [str(tool), "view", "--vault-password-file", str(key), str(vault)],
            capture_output=True, check=True,
        )
        values = json.loads(decrypted.stdout)
        required = ("tms_database_deployment_id", "tms_database_password", "tms_keycloak_database_password")
        if not all(values.get(name) for name in required):
            raise SystemExit("The existing vault is missing required fields. Restore it; do not regenerate passwords.")
        print("Reusing the existing encrypted deployment credentials; no passwords changed.")
        return
    values = {
        "tms_database_deployment_id": uuid.uuid4().hex,
        "tms_database_password": secrets.token_urlsafe(36),
        "tms_keycloak_database_password": secrets.token_urlsafe(36),
    }
    with key.open("x") as output:
        output.write(secrets.token_urlsafe(48) + "\n")
    # Plaintext is supplied through stdin only. The on-disk temporary file is ciphertext.
    encrypted = directory / "vault.new"
    if encrypted.exists():
        raise SystemExit("An unfinished vault file exists; inspect the secrets directory before continuing.")
    subprocess.run(
        [str(tool), "encrypt", "--vault-password-file", str(key), "--output", str(encrypted), "-"],
        input=json.dumps(values).encode(), capture_output=True, check=True,
    )
    encrypted.chmod(0o600)
    encrypted.replace(vault)
    print("Created encrypted deployment credentials. Keep the controller's secrets directory for subsequent runs and recovery.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        # Do not include subprocess input/output or decrypted content in an error report.
        sys.exit("Vault operation failed. Existing files were preserved; check the private vault/key pair locally.")
