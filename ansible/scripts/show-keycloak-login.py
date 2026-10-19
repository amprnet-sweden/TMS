#!/usr/bin/env python3
"""Display one human login on explicit operator request; never used by provisioning."""
import argparse

from controller import Vault, run_cli


def main():
    parser = argparse.ArgumentParser(description="Show a login locally. Do not paste its output into chat or logs.")
    parser.add_argument("account", choices=("tms-admin", "appuser"))
    args = parser.parse_args()
    field = "tms_keycloak_admin_password" if args.account == "tms-admin" else "tms_keycloak_operator_password"
    values = Vault().read((field,))
    print("Username:", args.account)
    print("Password:", values[field])


if __name__ == "__main__":
    run_cli(main)
