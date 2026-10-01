#!/usr/bin/env bash
set -euo pipefail

# Run on Linux or in WSL. Everything lives in a dedicated user directory; no sudo.
controller_dir="${TMS_CONTROLLER_DIR:-$HOME/.local/share/tms-ansible}"
mkdir -p "$controller_dir"
python3 -m pip install --disable-pip-version-check --target "$controller_dir/bootstrap" 'uv==0.12.20'
export UV_PYTHON_INSTALL_DIR="$controller_dir/python"
export UV_CACHE_DIR="$controller_dir/cache"
uv="$controller_dir/bootstrap/bin/uv"
"$uv" python install 3.13.15
"$uv" venv --python 3.13.15 --allow-existing "$controller_dir/venv"
"$uv" pip install --python "$controller_dir/venv/bin/python" 'ansible-core==2.21.4' 'cryptography==50.0.1'
"$controller_dir/venv/bin/ansible" --version
