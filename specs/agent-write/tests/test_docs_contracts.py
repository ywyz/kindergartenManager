"""文档账本中的 commit 引用必须可在 git 中解析。"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LEDGER_PATH = Path("specs/agent-write/tests/README.md")

LINE_TAG_PATTERN = re.compile(
    r"\b(?:commit|sha|red|green|closure|tested_code_sha|evidence_closure_sha)\b",
    re.IGNORECASE,
)

FULL_COMMIT_HASH_PATTERN = re.compile(r"(?<![0-9a-f])([0-9a-f]{40})(?![0-9a-f])")
RG_CONTEXT_KEYWORDS = ("finding", "candidate", "前检", "最小", "commit", "固定", "由")


def _extract_tagged_shas(ledger: str) -> list[str]:
    lines = ledger.splitlines()
    tagged_shas: set[str] = set()

    for index, line in enumerate(lines):
        if not LINE_TAG_PATTERN.search(line):
            continue

        context_lines = "\n".join(lines[max(0, index - 1) : index + 2]).lower()
        if "node hash" in context_lines:
            continue

        # avoid matching a 40-char slice inside 64-char digests like sha256
        for match in FULL_COMMIT_HASH_PATTERN.finditer(line):
            sha = match.group(1)
            context = f"{line}\n{context_lines}".lower()

            if "sha256" in context:
                continue

            has_explicit_tag = any(
                token in context
                for token in (
                    "tested_code_sha",
                    "evidence_closure_sha",
                    "commit",
                    "closure",
                )
            )
            if has_explicit_tag:
                tagged_shas.add(sha)
                continue

            has_rgb_anchor = bool(re.search(r"\b(?:red|green)\b", context))
            has_rgb_context = any(token in context for token in RG_CONTEXT_KEYWORDS)
            if has_rgb_anchor and has_rgb_context:
                tagged_shas.add(sha)

    return sorted(tagged_shas)


def test_canonical_ledger_tagged_git_references_resolve_to_commits() -> None:
    """Canonical ledger references that look like commit hashes must exist as git commits."""
    ledger = (REPO_ROOT / LEDGER_PATH).read_text(encoding="utf-8")

    tagged_shas = _extract_tagged_shas(ledger)

    assert tagged_shas, "No tagged 40-hex references found in canonical ledger"

    missing: list[str] = []
    for sha in tagged_shas:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "cat-file", "-e", f"{sha}^{{commit}}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            missing.append(sha)

    assert not missing, (
        "Canonical ledger tagged 40-hex references must resolve as commits: "
        + ", ".join(sorted(set(missing)))
    )
