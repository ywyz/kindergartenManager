"""Run WP-A gap probes twice in private, disposable settings directories.

The caller supplies the repository's Python executable. No production URL,
credential file, migration, UI server, or real AI is used by this runner.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
SUITE = "specs/weekly-plan-authoring/tests/test_current_behavior_gaps.py"


def run() -> None:
    results = []
    for index in (1, 2):
        with tempfile.TemporaryDirectory(prefix="km-wpa-red-") as temporary:
            os.chmod(temporary, 0o700)
            env = os.environ.copy()
            env.update(
                KINDERGARTEN_DATA_DIR=temporary,
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                PYTHONDONTWRITEBYTECODE="1",
            )
            args = [
                sys.executable,
                "-m",
                "pytest",
                SUITE,
                "-vv",
                "--tb=short",
                "-p",
                "no:cacheprovider",
            ]
            result = subprocess.run(
                args, cwd=ROOT, env=env, text=True, capture_output=True, check=False
            )
            output = result.stdout + result.stderr
            (OUTPUT / f"red-run-{index}.log").write_text(output)
            nodes = [
                line.split(" ")[0]
                for line in output.splitlines()
                if line.startswith(SUITE + "::")
                and (" PASSED " in line or " FAILED " in line)
            ]
            outcomes = [
                line.split(" ")[1]
                for line in output.splitlines()
                if line.startswith(SUITE + "::")
                and (" PASSED " in line or " FAILED " in line)
            ]
            manifest = "\n".join(nodes) + "\n"
            (OUTPUT / f"red-nodes-{index}.txt").write_text(manifest)
            results.append(
                {
                    "run": index,
                    "exit": result.returncode,
                    "collected": len(nodes),
                    "passed": outcomes.count("PASSED"),
                    "failed": outcomes.count("FAILED"),
                    "node_sha256": hashlib.sha256(manifest.encode()).hexdigest(),
                    "outcomes": outcomes,
                }
            )
    report = {
        "source_sha": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "test_sha256": hashlib.sha256((ROOT / SUITE).read_bytes()).hexdigest(),
        "results": results,
    }
    (OUTPUT / "red-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not all(
        item["exit"] == 1
        and item["collected"] == 16
        and item["failed"] == 12
        and item["passed"] == 4
        for item in results
    ):
        raise SystemExit("Unexpected RED distribution; inspect logs")
    if (
        results[0]["node_sha256"] != results[1]["node_sha256"]
        or results[0]["outcomes"] != results[1]["outcomes"]
    ):
        raise SystemExit("Unstable RED nodes/outcomes")


if __name__ == "__main__":
    run()
