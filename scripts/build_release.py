#!/usr/bin/env python3
"""Build the deterministic WorkBuddy/Codex/Claude Agent Skill archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "cyber-bookhouse"
SOURCE = ROOT / "skills" / SKILL_NAME
DEFAULT_OUTPUT = ROOT / "dist" / "cyber-bookhouse.zip"
REQUIRED = (
    "LICENSE",
    "SKILL.md",
    "release.json",
    "scripts/install_skill.py",
    "scripts/update_skill.py",
    "scripts/setup_state.py",
    "scripts/validate_note.py",
    "scripts/visual_gate.py",
    "references/codex.md",
    "references/claude.md",
    "references/workbuddy.md",
    "references/obsidian.md",
    "references/note-modes.md",
    "references/response-style.md",
)
IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def included_files() -> list[Path]:
    missing = [name for name in REQUIRED if not (SOURCE / name).is_file()]
    if missing:
        raise ValueError(f"Missing required skill files: {', '.join(missing)}")
    files = []
    for path in sorted(SOURCE.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(SOURCE)
        if any(part in IGNORED_NAMES for part in relative.parts):
            continue
        if relative.suffix in IGNORED_SUFFIXES:
            continue
        files.append(path)
    return files


def build(output: Path) -> dict[str, object]:
    files = included_files()
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = Path(SKILL_NAME) / path.relative_to(SOURCE)
            info = zipfile.ZipInfo(relative.as_posix(), ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "output": str(output),
        "sha256": digest,
        "files": len(files),
        "bytes": output.stat().st_size,
        "layout": f"{SKILL_NAME}/SKILL.md",
        "targets": ["Codex", "Claude Code", "WorkBuddy"],
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return value


def main() -> int:
    try:
        args = parser().parse_args()
        print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
