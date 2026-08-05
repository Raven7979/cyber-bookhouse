#!/usr/bin/env python3
"""Install this portable skill for Codex, Claude Code, or both."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


SKILL_NAME = "cyber-bookhouse"
# Preserve an existing pre-rename install as a recoverable backup.
LEGACY_SKILL_NAMES = ("sanwei",)
TARGET_DIRS = {
    "codex": Path(".agents") / "skills" / SKILL_NAME,
    "claude": Path(".claude") / "skills" / SKILL_NAME,
}
IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def manifest(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if should_ignore(relative):
            continue
        result[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_source(source: Path) -> None:
    entrypoint = source / "SKILL.md"
    if not entrypoint.is_file():
        raise ValueError(f"SKILL.md not found in {source}")
    text = entrypoint.read_text(encoding="utf-8")
    if f"name: {SKILL_NAME}" not in text.split("---", 2)[1]:
        raise ValueError(f"SKILL.md does not declare name: {SKILL_NAME}")


def copy_filter(_: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in IGNORED_NAMES or Path(name).suffix in IGNORED_SUFFIXES
    }


def install_one(
    source: Path, destination: Path, backup_directory: Path
) -> dict[str, object]:
    source = source.resolve()
    destination = destination.expanduser()
    if destination.exists() and destination.resolve() == source:
        return {
            "status": "already_installed",
            "destination": str(destination),
            "backup": None,
        }

    source_manifest = manifest(source)
    if destination.is_dir() and manifest(destination) == source_manifest:
        return {
            "status": "already_current",
            "destination": str(destination),
            "backup": None,
        }

    destination.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if destination.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_directory.mkdir(parents=True, exist_ok=True)
        backup = backup_directory / f"{SKILL_NAME}-{stamp}"
        counter = 1
        while backup.exists():
            backup = backup_directory / f"{SKILL_NAME}-{stamp}-{counter}"
            counter += 1
        destination.replace(backup)

    temp_root = Path(tempfile.mkdtemp(prefix=f".{SKILL_NAME}-", dir=destination.parent))
    staged = temp_root / SKILL_NAME
    try:
        shutil.copytree(source, staged, ignore=copy_filter)
        os.replace(staged, destination)
    except Exception:
        if not destination.exists() and backup and backup.exists():
            os.replace(backup, destination)
        raise
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    if manifest(destination) != source_manifest:
        raise RuntimeError(f"Installed files failed read-back verification: {destination}")
    return {
        "status": "installed",
        "destination": str(destination),
        "backup": str(backup) if backup else None,
    }


def archive_legacy_installs(
    source: Path, skills_directory: Path, backup_directory: Path
) -> list[str]:
    backups: list[str] = []
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for legacy_name in LEGACY_SKILL_NAMES:
        legacy = skills_directory / legacy_name
        if not legacy.exists():
            continue
        if legacy.resolve() == source.resolve():
            continue
        backup_directory.mkdir(parents=True, exist_ok=True)
        backup = backup_directory / f"{legacy_name}-{stamp}"
        counter = 1
        while backup.exists():
            backup = backup_directory / f"{legacy_name}-{stamp}-{counter}"
            counter += 1
        legacy.replace(backup)
        backups.append(str(backup))
    return backups


def install(target: str, home: Path | None = None) -> dict[str, object]:
    source = skill_root()
    validate_source(source)
    home = (home or Path.home()).expanduser()
    selected = tuple(TARGET_DIRS) if target == "both" else (target,)
    results = {}
    for name in selected:
        destination = home / TARGET_DIRS[name]
        backup_directory = home / ".cyber-bookhouse-backups" / name
        result = install_one(source, destination, backup_directory)
        result["legacy_backups"] = archive_legacy_installs(
            source,
            destination.parent,
            backup_directory,
        )
        results[name] = result
    return {
        "skill": SKILL_NAME,
        "source": str(source),
        "results": results,
        "next_step": f"Open a new task and invoke {SKILL_NAME} explicitly once.",
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--target", choices=("codex", "claude", "both"), required=True
    )
    value.add_argument(
        "--home",
        type=Path,
        help="Override the user home directory. Intended for testing or managed installs.",
    )
    return value


def main() -> int:
    try:
        args = parser().parse_args()
        print(json.dumps(install(args.target, args.home), ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
