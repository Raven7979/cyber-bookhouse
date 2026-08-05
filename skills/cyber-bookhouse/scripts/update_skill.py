#!/usr/bin/env python3
"""Check and safely update the installed cyber-bookhouse Skill from GitHub."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse


SKILL_NAME = "cyber-bookhouse"
REPOSITORY = "Raven7979/cyber-bookhouse"
LATEST_RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
ASSET_NAME = "cyber-bookhouse.zip"
MAX_DOWNLOAD_BYTES = 20 * 1024 * 1024
MAX_UNPACKED_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_FILES = 500
ALLOWED_DOWNLOAD_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}
BUILD_MARKER = re.compile(r"<!--\s*cyber-bookhouse-build:\s*(\d+)\s*-->")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_identity(root: Path) -> dict[str, object]:
    path = root / "release.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("version")
    build = payload.get("build")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"Invalid version in {path}")
    if not isinstance(build, int) or build < 1:
        raise ValueError(f"Invalid build in {path}")
    return {"version": version, "build": build}


def version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError(f"Invalid release version: {value}")
    return tuple(int(part) for part in match.groups())


def request_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{SKILL_NAME}-updater",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if urlparse(response.geturl()).hostname != "api.github.com":
            raise ValueError("GitHub API redirected to an unexpected host")
        data = json.load(response)
    if not isinstance(data, dict):
        raise ValueError("GitHub returned an invalid release response")
    return data


def latest_release() -> dict[str, object]:
    data = request_json(LATEST_RELEASE_API)
    if data.get("draft") or data.get("prerelease"):
        raise ValueError("GitHub Latest Release is not a stable published release")
    tag = data.get("tag_name")
    body = data.get("body") or ""
    if not isinstance(tag, str):
        raise ValueError("GitHub release is missing tag_name")
    version_tuple(tag)
    marker = BUILD_MARKER.search(body) if isinstance(body, str) else None
    if marker is None:
        raise ValueError("GitHub release is missing the build marker")
    assets = data.get("assets")
    if not isinstance(assets, list):
        raise ValueError("GitHub release is missing assets")
    asset = next(
        (
            item
            for item in assets
            if isinstance(item, dict)
            and item.get("name") == ASSET_NAME
            and item.get("state") == "uploaded"
        ),
        None,
    )
    if asset is None:
        raise ValueError(f"GitHub release is missing uploaded asset {ASSET_NAME}")
    digest = asset.get("digest")
    if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise ValueError("GitHub release asset is missing a valid SHA-256 digest")
    download_url = asset.get("browser_download_url")
    if not isinstance(download_url, str):
        raise ValueError("GitHub release asset is missing its download URL")
    return {
        "version": tag.removeprefix("v"),
        "build": int(marker.group(1)),
        "tag": tag,
        "download_url": download_url,
        "sha256": digest.removeprefix("sha256:"),
        "release_url": data.get("html_url"),
    }


def update_available(current: dict[str, object], latest: dict[str, object]) -> bool:
    current_version = version_tuple(str(current["version"]))
    latest_version = version_tuple(str(latest["version"]))
    if latest_version != current_version:
        return latest_version > current_version
    return int(latest["build"]) > int(current["build"])


def download_asset(release: dict[str, object], destination: Path) -> None:
    url = str(release["download_url"])
    if urlparse(url).scheme != "https" or urlparse(url).hostname != "github.com":
        raise ValueError("Release asset URL is not the expected GitHub HTTPS URL")
    request = urllib.request.Request(url, headers={"User-Agent": f"{SKILL_NAME}-updater"})
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        final_url = urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname not in ALLOWED_DOWNLOAD_HOSTS:
            raise ValueError("Release download redirected to an unexpected host")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                raise ValueError("Release archive exceeds the download size limit")
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != release["sha256"]:
        raise ValueError("Release archive SHA-256 does not match GitHub metadata")


def validate_and_extract(
    archive_path: Path, destination: Path, release: dict[str, object]
) -> Path:
    required = {
        f"{SKILL_NAME}/SKILL.md",
        f"{SKILL_NAME}/release.json",
        f"{SKILL_NAME}/scripts/install_skill.py",
        f"{SKILL_NAME}/scripts/update_skill.py",
    }
    with zipfile.ZipFile(archive_path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ARCHIVE_FILES:
            raise ValueError("Release archive contains too many files")
        total_size = 0
        names: set[str] = set()
        for info in infos:
            name = info.filename
            path = PurePosixPath(name)
            if (
                not name
                or name.startswith("/")
                or "\\" in name
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != SKILL_NAME
            ):
                raise ValueError(f"Unsafe path in release archive: {name}")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"Symbolic links are not allowed in release archive: {name}")
            normalized_name = name.rstrip("/")
            if normalized_name in names:
                raise ValueError(f"Duplicate path in release archive: {name}")
            total_size += info.file_size
            if total_size > MAX_UNPACKED_BYTES:
                raise ValueError("Release archive exceeds the unpacked size limit")
            names.add(normalized_name)
        if not required.issubset(names):
            missing = ", ".join(sorted(required - names))
            raise ValueError(f"Release archive is missing required files: {missing}")
        archive.extractall(destination)
    extracted = destination / SKILL_NAME
    identity = load_identity(extracted)
    if identity["version"] != release["version"] or identity["build"] != release["build"]:
        raise ValueError("Release archive identity does not match GitHub release metadata")
    skill_text = (extracted / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = skill_text.split("---", 2)[1]
    if f"name: {SKILL_NAME}" not in frontmatter:
        raise ValueError("Release archive declares the wrong Skill name")
    return extracted


def infer_target(root: Path, home: Path) -> str:
    resolved = root.resolve()
    candidates = {
        "codex": (home / ".agents" / "skills" / SKILL_NAME).resolve(),
        "claude": (home / ".claude" / "skills" / SKILL_NAME).resolve(),
    }
    for target, candidate in candidates.items():
        if resolved == candidate:
            return target
    raise ValueError(
        "Cannot infer the installed target; use --target codex, claude, or both"
    )


def check() -> dict[str, object]:
    current = load_identity(skill_root())
    latest = latest_release()
    return {
        "skill": SKILL_NAME,
        "current": current,
        "latest": {key: latest[key] for key in ("version", "build", "release_url")},
        "update_available": update_available(current, latest),
    }


def apply_update(target: str, home: Path | None = None) -> dict[str, object]:
    root = skill_root()
    current = load_identity(root)
    release = latest_release()
    if not update_available(current, release):
        return {
            "skill": SKILL_NAME,
            "status": "already_current",
            "current": current,
            "latest": {key: release[key] for key in ("version", "build", "release_url")},
        }
    selected_home = (home or Path.home()).expanduser()
    selected_target = infer_target(root, selected_home) if target == "auto" else target
    with tempfile.TemporaryDirectory(prefix=f"{SKILL_NAME}-update-") as folder:
        temp_root = Path(folder)
        archive = temp_root / ASSET_NAME
        download_asset(release, archive)
        extracted = validate_and_extract(archive, temp_root / "unpacked", release)
        command = [
            sys.executable,
            str(extracted / "scripts" / "install_skill.py"),
            "--target",
            selected_target,
        ]
        if home is not None:
            command.extend(("--home", str(selected_home)))
        run = subprocess.run(command, check=True, capture_output=True, text=True)
        install_result = json.loads(run.stdout)
    return {
        "skill": SKILL_NAME,
        "status": "updated",
        "from": current,
        "to": {"version": release["version"], "build": release["build"]},
        "release_url": release["release_url"],
        "sha256": release["sha256"],
        "install": install_result,
        "next_step": "Restart or open a new Agent task before using the updated Skill.",
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    action = value.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--apply", action="store_true")
    value.add_argument(
        "--target",
        choices=("auto", "codex", "claude", "both"),
        default="auto",
    )
    value.add_argument("--home", type=Path, help=argparse.SUPPRESS)
    return value


def main() -> int:
    try:
        args = parser().parse_args()
        result = check() if args.check else apply_update(args.target, args.home)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (
        json.JSONDecodeError,
        IndexError,
        KeyError,
        OSError,
        subprocess.CalledProcessError,
        TypeError,
        urllib.error.URLError,
        ValueError,
        zipfile.BadZipFile,
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
