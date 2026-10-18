#!/usr/bin/env python3
"""Add Keycloak credentials atomically; preserve all existing database credentials."""
import secrets

from controller import ControllerError, DATABASE_FIELDS, Vault, require_fields, run_cli

FIELDS = ("tms_keycloak_bootstrap_password", "tms_keycloak_admin_password",
          "tms_keycloak_lookup_password", "tms_keycloak_operator_password")


def main():
    vault = Vault()
    values = vault.read(DATABASE_FIELDS)
    if all(name in values for name in FIELDS):
        require_fields(values, FIELDS, "Incomplete Keycloak credentials; restore the original vault rather than regenerating passwords.")
        print("Reusing encrypted Keycloak credentials; no passwords changed.")
        return
    if any(name in values for name in FIELDS):
        raise ControllerError("Incomplete Keycloak credentials; restore the original vault rather than regenerating passwords.")
    values.update({name: secrets.token_urlsafe(36) for name in FIELDS})
    vault.update(values)
    print("Added encrypted Keycloak credentials; existing database credentials preserved.")


if __name__ == "__main__":
    run_cli(main)
