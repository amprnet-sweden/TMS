#!/usr/bin/env python3
"""Generate general deployment variables without accessing certificates or credentials."""
from pathlib import Path
import sys

from controller import run_cli, write_variables
from deployment import load


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: prepare-deployment.py DEPLOYMENT.json")
    write_variables("deployment-vars.json", load(Path(sys.argv[1])))
    print("Deployment settings validated and prepared independently of TLS.")


if __name__ == "__main__":
    run_cli(main)
