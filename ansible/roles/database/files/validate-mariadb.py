#!/usr/bin/env python3
"""Validate a candidate in MariaDB's permitted config tree without changing it."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    # Ubuntu's confined mariadbd cannot read Ansible's private home-directory
    # staging path. This root-owned 0600 file is not included by *.cnf globs
    # under mariadb.conf.d, and is removed even when validation fails.
    with tempfile.TemporaryDirectory(prefix='.tms-validate-', dir='/etc/mysql') as directory:
        candidate = Path(directory) / 'candidate.cnf'
        shutil.copyfile(sys.argv[1], candidate)
        candidate.chmod(0o600)
        result = subprocess.run(
            ['/usr/sbin/mariadbd', f'--defaults-file={candidate}', '--verbose', '--help'],
            capture_output=True, timeout=60)
        if result.returncode:
            sys.stderr.buffer.write(result.stderr)
        return result.returncode


if __name__ == '__main__':
    sys.exit(main())
