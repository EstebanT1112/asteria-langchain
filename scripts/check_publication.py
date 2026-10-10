"""Comprueba que el paquete público no contenga secretos o archivos locales."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRECTORIES = {".git", ".venv", "__pycache__", "referencias"}
EXCLUDED_FILES = {".env"}
EXCLUDED_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".png", ".jpg", ".jpeg", ".pdf", ".docx"}
SECRET_PATTERNS = {
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    "OpenAI API key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(r"gh[oprsu]_[A-Za-z0-9]{20,}"),
    "private key": re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
}


def is_public_candidate(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
        return False
    if path.name in EXCLUDED_FILES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def main() -> int:
    findings: list[tuple[Path, str]] = []
    for path in ROOT.rglob("*"):
        if not is_public_candidate(path):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append((path.relative_to(ROOT), label))

    required = [
        ROOT / ".env.example",
        ROOT / ".gitignore",
        ROOT / "README.md",
        ROOT / "requirements.txt",
        ROOT / ".github" / "workflows" / "tests.yml",
    ]
    for path in required:
        if not path.is_file():
            findings.append((path.relative_to(ROOT), "required file missing"))

    if findings:
        for path, label in findings:
            print(f"FAIL: {path} ({label})")
        return 1

    print("PASS: no se detectaron secretos en los archivos publicables")
    print("PASS: están presentes los archivos necesarios para reproducir el proyecto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
