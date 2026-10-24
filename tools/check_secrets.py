"""Small local secret tripwire; broader supply-chain scanning remains a release gate."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "__pycache__", ".pytest_cache"}
PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
}


def hits(text: str) -> list[str]:
    return [name for name, pattern in PATTERNS.items() if pattern.search(text)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        planted = "AKIA" + "A" * 16
        assert "AWS access key" in hits(planted)
        assert hits("fictional local-demo-only password") == []
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for kind in hits(content):
            findings.append(f"{path.relative_to(ROOT)}: {kind}")
    if findings:
        raise SystemExit("\n".join(findings))
    print("No matching credential patterns found; planted-key self-test passed." if args.self_test else "No matching credential patterns found.")


if __name__ == "__main__":
    main()
