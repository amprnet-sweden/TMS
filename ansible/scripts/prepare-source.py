#!/usr/bin/env python3
"""Make a deterministic source snapshot of tracked application files plus the lockfile.

Local secrets, node_modules and build outputs are never recursively copied.
This is explicitly a working-tree snapshot, not a claim of a committed release.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile


def git(root, *arguments):
    return subprocess.check_output(["git", "-C", str(root), *arguments])


def normalized_content(path):
    content = path.read_bytes()
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    return content.replace(b"\r\n", b"\n") if b"\0" not in content else content


def main():
    ansible = Path(__file__).resolve().parents[1]
    root = ansible.parent
    local = ansible / ".local"
    local.mkdir(exist_ok=True)
    build = (root / "backend/build.gradle").read_text()
    if not re.search(r"JavaLanguageVersion\.of\(21\)", build):
        raise SystemExit("The source must select the Java 21 compiler before building.")
    package = json.loads((root / "frontend/package.json").read_text())
    lock_path = root / "frontend/package-lock.json"
    if not lock_path.exists():
        raise SystemExit("Generate frontend/package-lock.json using the pinned Node 22 first.")
    lock = json.loads(lock_path.read_text())
    for field in ("dependencies", "devDependencies"):
        if lock.get("packages", {}).get("", {}).get(field) != package.get(field):
            raise SystemExit(f"The lockfile does not match package.json {field}.")

    files = {}
    for entry in git(root, "ls-files", "--stage", "-z", "--", "backend", "frontend").split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, _, stage = metadata.decode().split()
        if stage != "0" or mode not in ("100644", "100755"):
            raise SystemExit(f"Unsupported source entry or unresolved merge: {name!r}")
        files[name.decode()] = 0o755 if mode == "100755" else 0o644
    # This file may be newly added and not yet staged while developing the playbook.
    files["frontend/package-lock.json"] = 0o644
    files["backend/gradlew"] = 0o755
    temporary = local / "source.tmp.tar"
    with tarfile.open(temporary, "w", format=tarfile.USTAR_FORMAT) as archive:
        for name, mode in sorted(files.items()):
            path = root / name
            if path.is_symlink() or not path.is_file():
                raise SystemExit(f"Source must be a regular file: {name}")
            content = normalized_content(path)
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = mode
            info.mtime = 0
            archive.addfile(info, io.BytesIO(content))
    source_hash = hashlib.sha256(temporary.read_bytes()).hexdigest()
    destination = local / f"source-{source_hash}.tar"
    temporary.replace(destination)

    recipe = hashlib.sha256()
    recipe_files = [ansible / "build.yml", Path(__file__).resolve()]
    recipe_files += [path for role in ("build", "build_tools")
                     for path in (ansible / "roles" / role).rglob("*")
                     if path.is_file() and path.suffix in (".yml", ".j2", ".py")]
    for path in sorted(recipe_files):
        recipe.update(str(path.relative_to(ansible)).encode() + b"\0")
        recipe.update(normalized_content(path) + b"\0")
    variables = {
        "tms_source_archive": str(destination),
        "tms_source_sha256": source_hash,
        "tms_source_base_commit": git(root, "rev-parse", "HEAD").decode().strip(),
        "tms_build_recipe_sha256": recipe.hexdigest(),
    }
    (local / "source-vars.json").write_text(json.dumps(variables, indent=2) + "\n")
    print(f"Prepared {len(files)} source files; SHA256 {source_hash}")
    print("Source: local development snapshot, including uncommitted application edits.")


if __name__ == "__main__":
    main()
