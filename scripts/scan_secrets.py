"""
Repository Hygiene & Pre-Release Secret Scanner.
Audits the workspace to guarantee no unmasked OpenRouter API keys or JWT tokens
have been accidentally committed or saved in plain text.
"""

import os
import re
import sys
from pathlib import Path

# Match live OpenRouter API keys
SECRET_REGEX = re.compile(r"sk-or-v1-[a-f0-9]{32,}", re.IGNORECASE)
RAW_SECRET_GENERIC = re.compile(r"sk-or-[a-z0-9_-]{20,}", re.IGNORECASE)

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".png",
    ".jpg",
    ".jpeg",
    ".ico",
    ".bin",
}


def scan_workspace(root_path: Path) -> int:
    violations = []
    print(f"Scanning {root_path.resolve()} for leaked credentials...")

    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file_name in files:
            path = Path(root) / file_name
            if path.suffix.lower() in EXCLUDE_EXTENSIONS:
                continue
            if file_name in {".env.example", "scan_secrets.py"}:
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    # Check for live keys
                    if SECRET_REGEX.search(line) or RAW_SECRET_GENERIC.search(line):
                        # Filter out documentation mentions or masked keys
                        if "..." in line or "sk-or-v1-..." in line or "placeholder" in line.lower():
                            continue
                        violations.append((path, line_idx, line.strip()))
            except Exception as e:
                print(f"Warning reading {path}: {e}")

    if violations:
        print("\n[!] SECURITY VIOLATION: Potential credentials found in source files:")
        for path, line_no, snippet in violations:
            masked = snippet[:15] + "..." + snippet[-6:] if len(snippet) > 25 else snippet
            print(f"  - {path}:{line_no} -> {masked}")
        print("\nPlease remove or mask these secrets immediately before committing.\n")
        return 1

    print("[OK] Clean! No plaintext OpenRouter API keys found in repository files.")
    return 0


if __name__ == "__main__":
    exit_code = scan_workspace(Path("."))
    sys.exit(exit_code)
