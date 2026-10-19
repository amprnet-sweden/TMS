"""Shared controller storage and vault I/O; callers decide when to create credentials."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

DATABASE_FIELDS = ("tms_database_deployment_id", "tms_database_password", "tms_keycloak_database_password")


class ControllerError(ValueError):
    """An operator-facing error that contains no private file contents."""


def controller_directory():
    return Path(os.environ.get("TMS_CONTROLLER_DIR", Path.home() / ".local/share/tms-ansible"))


def local_directory():
    directory = Path(__file__).resolve().parents[1] / ".local"
    directory.mkdir(exist_ok=True)
    return directory


def write_variables(name, values, directory=None):
    directory = Path(directory) if directory is not None else local_directory()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(values, indent=2) + "\n")


def require_fields(values, fields, message):
    if not isinstance(values, dict) or not all(isinstance(values.get(name), str) and values[name] for name in fields):
        raise ControllerError(message)


def run_cli(main):
    try:
        main()
    except ControllerError as error:
        sys.exit(str(error))
    except (OSError, ValueError, subprocess.CalledProcessError):
        # Never report subprocess input/output, decrypted JSON or private file contents.
        sys.exit("Controller operation failed. Check deployment settings and the original private files locally; "
                 "credentials will not be regenerated.")


class Vault:
    def __init__(self, controller=None):
        self.controller = Path(controller) if controller is not None else controller_directory()
        self.directory = self.controller / "secrets"
        self.key = self.directory / "vault.key"
        self.path = self.directory / "vault.yml"
        self.tool = self.controller / "venv/bin/ansible-vault"

    def exists(self):
        if self.directory.is_symlink() or (self.directory.exists() and not self.directory.is_dir()):
            raise ControllerError("Refusing to use a symlink or non-directory for the secrets directory.")
        for path in (self.key, self.path):
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise ControllerError("Refusing to use symlinked or non-regular vault files.")
        if self.key.exists() != self.path.exists():
            raise ControllerError("Incomplete vault/key pair. Restore the original pair; credentials will not be regenerated.")
        return self.key.exists()

    def read(self, fields=()):
        if not self.exists():
            raise ControllerError("The original private vault/key pair is required; run the database stage first.")
        self._protect()
        decrypted = subprocess.run(
            [str(self.tool), "view", "--vault-password-file", str(self.key), str(self.path)],
            capture_output=True, check=True,
        )
        values = json.loads(decrypted.stdout)
        require_fields(values, fields, "The existing vault is missing required fields. Restore it; do not regenerate passwords.")
        return values

    def _protect(self):
        self.directory.chmod(0o700)
        for path in (self.key, self.path):
            path.chmod(0o600)

    def _pending(self, name):
        pending = self.directory / name
        if pending.exists() or pending.is_symlink():
            raise ControllerError("An unfinished vault update exists; inspect the private secrets directory.")
        return pending

    def _encrypt(self, values, pending):
        # Reserve the private output exclusively; only ciphertext is written to disk.
        with pending.open("xb"):
            pending.chmod(0o600)
        subprocess.run(
            [str(self.tool), "encrypt", "--vault-password-file", str(self.key), "--output", str(pending), "-"],
            input=json.dumps(values).encode(), capture_output=True, check=True,
        )
        pending.chmod(0o600)
        pending.replace(self.path)

    def create(self, values):
        if self.exists():
            raise ControllerError("An original vault already exists; credentials will not be replaced.")
        os.umask(0o077)
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.directory.chmod(0o700)
        pending = self._pending("vault.new")
        with self.key.open("x") as output:
            output.write(secrets.token_urlsafe(48) + "\n")
        self._encrypt(values, pending)

    def update(self, values):
        if not self.exists():
            raise ControllerError("The original private vault/key pair is required before updating credentials.")
        self._protect()
        self._encrypt(values, self._pending("keycloak-vault.new"))
