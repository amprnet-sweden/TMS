#!/usr/bin/env python3
"""Run a build without exposing arbitrary compiler/package output.

Keep only fixed, recognized milestones in a bounded, live status file. Raw output
is consumed and discarded: it may contain credentials, URLs or environment data.
The Ansible async deadline remains responsible for terminating timed-out builds.
"""
from collections import deque
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


GRADLE_TASKS = frozenset("compileJava processResources classes resolveMainClassName bootJar jar "
                         "assemble check build compileTestJava processTestResources testClasses".split())


def milestone(line):
    match = re.fullmatch(r"> Task :(\w+)(?: (?:UP-TO-DATE|NO-SOURCE|FROM-CACHE|SKIPPED|FAILED))?", line)
    if match and match[1] in GRADLE_TASKS:
        return "Gradle task: " + match[1]
    if re.fullmatch(r"BUILD (?:SUCCESSFUL|FAILED) in [0-9hms .]+", line):
        return line
    if re.fullmatch(r"added \d+ packages(?:, and audited \d+ packages)? in [0-9.ms]+", line):
        return line
    if re.fullmatch(r"[✓✔] \d+ modules transformed\.", line):
        return "Vite modules transformed: " + re.search(r"\d+", line)[0]
    if line in ("transforming...", "rendering chunks...", "computing gzip size..."):
        return "Vite: " + line
    if re.fullmatch(r"[✓✔] built in [0-9.ms]+", line):
        return "Vite build completed"
    return None


def run(log, argv):
    started = time.monotonic()
    entries = deque(maxlen=40)

    def record(message):
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entries.append(f"[{stamp} +{time.monotonic() - started:.1f}s] {message}")
        # Create privately and atomically replace, never follow an existing log symlink.
        fd, temporary = tempfile.mkstemp(prefix=".build-status-", dir=log.parent)
        with os.fdopen(fd, "w") as stream:
            stream.write("\n".join(entries) + "\n")
        os.replace(temporary, log)

    record("Build started; silence is not evidence of a stalled build")
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError:
        record("Build executable could not be started")
        print("\n".join(entries), flush=True)
        return 127
    pending = b""
    oversized = False
    while chunk := process.stdout.read1(4096):
        for index, part in enumerate(chunk.split(b"\n")):
            if index:
                if not oversized:
                    message = milestone(pending.decode("utf-8", errors="replace").strip())
                    if message:
                        record(message)
                pending = b""
                oversized = False
            if len(pending) + len(part) > 4096:
                oversized = True
            if not oversized:
                pending += part
    if not oversized and pending:
        message = milestone(pending.decode("utf-8", errors="replace").strip())
        if message:
            record(message)
    process.stdout.close()
    code = process.wait()
    record(f"Build exited with status {code}")
    print("\n".join(entries), flush=True)
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    sys.exit(run(Path(sys.argv[1]), sys.argv[2:]))
