#!/usr/bin/env python3
"""Create a private deployment vault once; never print or silently replace credentials."""
import secrets
import uuid

from controller import DATABASE_FIELDS, Vault, run_cli


def main():
    vault = Vault()
    if vault.exists():
        vault.read(DATABASE_FIELDS)
        print("Reusing the existing encrypted deployment credentials; no passwords changed.")
        return
    vault.create({
        "tms_database_deployment_id": uuid.uuid4().hex,
        "tms_database_password": secrets.token_urlsafe(36),
        "tms_keycloak_database_password": secrets.token_urlsafe(36),
    })
    print("Created encrypted deployment credentials. Keep the controller's secrets directory for subsequent runs and recovery.")


if __name__ == "__main__":
    run_cli(main)
