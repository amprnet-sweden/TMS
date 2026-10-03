#!/usr/bin/env python3
"""Display one human login on explicit operator request; never used by provisioning."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description="Show a login locally. Do not paste its output into chat or logs.")
parser.add_argument("account", choices=("tms-admin", "appuser"))
args = parser.parse_args()
controller = Path(os.environ.get("TMS_CONTROLLER_DIR", Path.home() / ".local/share/tms-ansible"))
try:
    values = json.loads(subprocess.run([str(controller / "venv/bin/ansible-vault"), "view",
        "--vault-password-file", str(controller / "secrets/vault.key"),
        str(controller / "secrets/vault.yml")], capture_output=True, check=True).stdout)
    field = "tms_keycloak_admin_password" if args.account == "tms-admin" else "tms_keycloak_operator_password"
    print("Username:", args.account)
    print("Password:", values[field])
except (subprocess.CalledProcessError, ValueError, KeyError):
    sys.exit("Could not read this login from the original deployment vault.")
