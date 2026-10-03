#!/usr/bin/env bash
set -euo pipefail
ansible_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
controller_dir="${TMS_CONTROLLER_DIR:-$HOME/.local/share/tms-ansible}"
if [[ $# -ne 2 || ! -f "$1" || ! -f "$2" ]]; then
    echo 'Usage: bash install.sh INVENTORY.yml DEPLOYMENT.json' >&2
    exit 1
fi
inventory="$(realpath -- "$1")"
deployment="$(realpath -- "$2")"
export ANSIBLE_COLLECTIONS_PATH="$ansible_dir/.local/collections"
python="$controller_dir/venv/bin/python"
if [[ ! -x "$python" ]]; then
    echo 'Run bash scripts/setup-controller.sh first.' >&2
    exit 1
fi
"$python" "$ansible_dir/scripts/prepare-tls.py" "$deployment"
"$controller_dir/venv/bin/ansible-galaxy" collection install -r "$ansible_dir/requirements.yml" -p "$ANSIBLE_COLLECTIONS_PATH"
"$python" "$ansible_dir/scripts/prepare-source.py"
"$python" "$ansible_dir/scripts/prepare-database-vault.py"
"$python" "$ansible_dir/scripts/prepare-keycloak-vault.py"
echo 'BECOME password is the target account sudo password.'
exec "$controller_dir/venv/bin/ansible-playbook" -i "$inventory" "$ansible_dir/site.yml" \
    --extra-vars "@$ansible_dir/.local/source-vars.json" \
    --extra-vars "@$ansible_dir/.local/tls-vars.json" \
    --extra-vars "@$controller_dir/secrets/vault.yml" \
    --vault-password-file "$controller_dir/secrets/vault.key" --ask-become-pass
